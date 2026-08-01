"""
Modern Data Platform
Processing Framework

Postgres extraction stage.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from typing import cast

import psycopg
import pyarrow as pa
import pyarrow.parquet as pq
from psycopg import Column, sql

from data_platform.processing.context_writers.storage_context_writer import (
    StorageContextWriter,
)
from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult
from data_platform.storage.config import StorageConfig
from data_platform.storage.models import StorageLocation
from data_platform.storage.storage_provider import StorageProvider

from integrations.postgres.config import PostgresSettings

# Postgres type OID -> Arrow type, confirmed against every column type
# actually used in the marketplace schema (17 tables, checked via
# information_schema.columns/pg_type) -- not a generic Postgres type
# mapping, just the types this project's schema has today.
_NUMERIC_OID = 1700
_UUID_OID = 2950

_POSTGRES_OID_TO_ARROW: dict[int, pa.DataType] = {
    16: pa.bool_(),  # bool
    21: pa.int16(),  # smallint
    23: pa.int32(),  # integer
    25: pa.string(),  # text
    1043: pa.string(),  # varchar
    1082: pa.date32(),  # date
    1184: pa.timestamp("us", tz="UTC"),  # timestamptz
    # uuid: stored as plain text, not pa.uuid() -- Spark's Parquet
    # reader rejects the UUID logical type outright
    # ([PARQUET_TYPE_ILLEGAL] Illegal Parquet type:
    # FIXED_LEN_BYTE_ARRAY (UUID)), confirmed against a real
    # Databricks run. A plain string also matches how Debezium/Kafka
    # already represents the same column.
    _UUID_OID: pa.string(),
}


def _arrow_type_for_column(column: Column) -> pa.DataType:
    """
    Resolves the Arrow type for a Postgres column from its real type
    (``column.type_code``, the type OID psycopg always exposes via
    ``cursor.description``) -- not from the values fetched.

    This is what makes an empty result set produce a correct schema
    (e.g. a uuid column stays a uuid column with zero rows) instead of
    the all-``null`` schema pyarrow falls back to when it has no
    values to infer a type from. That mismatch is exactly what broke
    Spark's read of raw/{entity}/ once a real, populated extraction of
    the same table landed next to an earlier empty one.
    """

    if column.type_code == _NUMERIC_OID:

        if column.precision is None or column.scale is None:
            raise ValueError(
                f"Column '{column.name}' is numeric without a "
                "precision/scale -- add explicit handling before "
                "extracting it (every numeric column in the "
                "marketplace schema has both)."
            )

        return pa.decimal128(column.precision, column.scale)

    try:
        return _POSTGRES_OID_TO_ARROW[column.type_code]
    except KeyError:
        raise ValueError(
            f"Column '{column.name}' has Postgres type OID "
            f"{column.type_code}, which is not mapped to an Arrow "
            "type yet -- add it to _POSTGRES_OID_TO_ARROW before "
            "extracting it."
        ) from None


@dataclass(eq=False, slots=True, kw_only=True)
class PostgresExtractionStage(Stage):
    """
    Extracts a single Postgres table and lands it as a raw Parquet
    object in the Data Lake (``raw/{entity}/``) -- the file is a plain
    columnar snapshot, not yet a Delta table (that transformation
    happens downstream, in the Bronze layer).

    This Stage is intentionally specific to Postgres via psycopg, not
    behind a generic extraction/source Provider contract: with a
    single concrete source implemented, an abstracted contract would
    be speculative and easy to get the seams wrong on (the same
    failure mode the original ADR-010 audit found in capabilities
    designed ahead of any real implementation). A different source
    (a public API, a CSV drop, ...) gets its own Stage next to this
    one, in the same ``processing/extraction/`` package -- not a
    configuration knob on this one.

    A missing table is a business failure -- retrying will not make
    it appear -- so it is reported through a FAILED StageResult
    (mirroring how BronzeIngestionStage treats a missing storage
    object). Any other psycopg error (connection refused,
    authentication, ...) is a technical failure and is left to
    propagate, so RetryPolicy can act on it.
    """

    provider_name: str

    postgres_settings: PostgresSettings

    table_name: str

    entity: str

    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:

        try:
            table = self._extract()

        except psycopg.errors.UndefinedTable as error:
            return StageResult(
                status=ExecutionStatus.FAILED,
                metadata=context.metadata,
                stage_id=self.id,
                stage_name=self.name,
                error_type="UndefinedTable",
                error_message=str(error),
            )

        provider = cast(
            StorageProvider,
            self.resolve_provider(self.provider_name),
        )

        location = StorageLocation.from_uri(
            f"{StorageConfig.raw(self.entity)}/{uuid.uuid4()}.parquet"
        )

        provider.upload(
            location,
            self._to_parquet(table),
        )

        StorageContextWriter.write(
            location,
            context,
        )

        return StageResult(
            status=ExecutionStatus.COMPLETED,
            metadata=context.metadata,
            stage_id=self.id,
            stage_name=self.name,
        )

    def _extract(self) -> pa.Table:
        """
        Connects to Postgres and reads the full table into a
        pyarrow.Table.

        ``table_name`` is treated as an identifier, never interpolated
        as a raw value: it is split on "." (``schema.table`` or plain
        ``table``) and passed to ``psycopg.sql.Identifier``, which
        quotes each part individually. This is what actually prevents
        SQL injection through the table name -- not a regex check on
        the string.
        """

        identifier = sql.Identifier(*self.table_name.split("."))

        settings = self.postgres_settings

        with psycopg.connect(
            host=settings.host,
            port=settings.port,
            dbname=settings.database,
            user=settings.user,
            password=settings.password,
        ) as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    sql.SQL("SELECT * FROM {}").format(identifier)
                )

                description = cursor.description or []

                schema = pa.schema(
                    [
                        (column.name, _arrow_type_for_column(column))
                        for column in description
                    ]
                )

                rows = cursor.fetchall()

        return pa.table(
            {
                column.name: self._column_values(column, index, rows)
                for index, column in enumerate(description)
            },
            schema=schema,
        )

    @staticmethod
    def _column_values(
        column: Column,
        index: int,
        rows: list[tuple],
    ) -> list:
        """
        Reads one column's raw values out of the fetched rows.

        uuid columns get stringified here: psycopg returns them as
        ``uuid.UUID`` objects, but the Arrow schema types them as
        ``pa.string()`` (see _POSTGRES_OID_TO_ARROW), and pyarrow does
        not coerce UUID objects into strings on its own -- it raises
        ``Expected bytes, got a 'UUID' object`` if handed one directly.
        """

        values = [row[index] for row in rows]

        if column.type_code == _UUID_OID:
            return [
                str(value) if value is not None else None
                for value in values
            ]

        return values

    @staticmethod
    def _to_parquet(table: pa.Table) -> io.BytesIO:
        buffer = io.BytesIO()

        pq.write_table(table, buffer)

        buffer.seek(0)

        return buffer
