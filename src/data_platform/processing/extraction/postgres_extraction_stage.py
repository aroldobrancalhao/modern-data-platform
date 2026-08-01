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
from psycopg import sql

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

                columns = [
                    column.name for column in cursor.description or []
                ]

                rows = cursor.fetchall()

        return pa.table(
            {
                column: [row[index] for row in rows]
                for index, column in enumerate(columns)
            }
        )

    @staticmethod
    def _to_parquet(table: pa.Table) -> io.BytesIO:
        buffer = io.BytesIO()

        pq.write_table(table, buffer)

        buffer.seek(0)

        return buffer
