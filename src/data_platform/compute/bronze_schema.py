"""
Modern Data Platform

Resolves the exact Arrow schema Bronze expects for a given entity, by
querying Postgres directly -- the same source of truth
``PostgresExtractionStage`` reads from (see
``data_platform.processing.extraction.postgres_extraction_stage``),
just through ``information_schema.columns`` instead of
``cursor.description`` OIDs, since the Bronze Consumer never runs a
``SELECT`` against the table itself (it only ever sees Debezium change
events).

The type mapping below is deliberately kept in lockstep with
``PostgresExtractionStage._arrow_type_for_column`` -- both exist to
produce the identical Bronze schema for the same Postgres column,
whichever path (batch extraction or streaming CDC) writes it first.
Getting them out of sync would reintroduce the schema mismatch this
module exists to avoid.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import psycopg
import pyarrow as pa

from integrations.postgres.config import PostgresSettings

_DATA_TYPE_TO_ARROW: dict[str, pa.DataType] = {
    "boolean": pa.bool_(),
    "smallint": pa.int16(),
    "integer": pa.int32(),
    "text": pa.string(),
    "character varying": pa.string(),
    "date": pa.date32(),
    "timestamp with time zone": pa.timestamp("us", tz="UTC"),
    # uuid: plain string, not pa.uuid() -- mirrors
    # PostgresExtractionStage (Spark's Parquet reader rejects the UUID
    # logical type outright), and matches how Debezium already
    # represents the same column in the Kafka payload.
    "uuid": pa.string(),
}


def resolve_bronze_schema(
    entity: str,
    schema_name: str = "marketplace",
    postgres_settings: PostgresSettings | None = None,
) -> pa.Schema:
    """
    Builds the ``pa.Schema`` for ``entity`` from Postgres'
    ``information_schema.columns`` -- column order, names and types
    match exactly what ``PostgresExtractionStage`` would produce for
    the same table today.

    Raises ValueError if the table has no columns (typically a typo in
    ``entity``) or a column type outside ``_DATA_TYPE_TO_ARROW`` (add
    it there once a real column needs it -- same policy as
    ``PostgresExtractionStage``).
    """

    settings = postgres_settings or PostgresSettings()

    with psycopg.connect(
        host=settings.host,
        port=settings.port,
        dbname=settings.database,
        user=settings.user,
        password=settings.password,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT column_name, data_type, numeric_precision, numeric_scale
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """,
                (schema_name, entity),
            )

            rows = cursor.fetchall()

    if not rows:
        raise ValueError(
            f"No columns found for '{schema_name}.{entity}' -- check "
            "the entity name."
        )

    return pa.schema(
        [
            (
                column_name,
                _arrow_type(column_name, data_type, precision, scale),
            )
            for column_name, data_type, precision, scale in rows
        ]
    )


def coerce_record(record: dict[str, Any], schema: pa.Schema) -> dict[str, Any]:
    """
    Adjusts a Debezium-decoded record so pyarrow can build a row of
    ``schema`` (as resolved by ``resolve_bronze_schema``) from it.

    The project's Debezium connector runs with
    ``decimal.handling.mode: double`` (see
    ``infrastructure/docker/debezium/connectors/marketplace-postgres.json``),
    so every Postgres ``numeric`` column arrives here as a Python
    float rather than a Decimal -- pyarrow refuses to build a
    ``decimal128`` array straight from floats, since binary
    floating-point cannot exactly represent most decimal fractions.
    Each such value is rounded to its field's own scale and routed
    through its string representation before becoming a ``Decimal``,
    which avoids baking in the float's binary rounding error.

    Every other field is returned unchanged -- pyarrow already builds
    the rest of ``schema``'s types directly from the plain Python
    values ``decode_debezium_message`` produces.
    """

    coerced = dict(record)

    for field in schema:

        if not pa.types.is_decimal(field.type):
            continue

        value = coerced.get(field.name)

        if isinstance(value, float):
            coerced[field.name] = Decimal(str(round(value, field.type.scale)))

    return coerced


def _arrow_type(
    column_name: str,
    data_type: str,
    precision: int | None,
    scale: int | None,
) -> pa.DataType:

    if data_type == "numeric":

        if precision is None or scale is None:
            raise ValueError(
                f"Column '{column_name}' is numeric without a "
                "precision/scale -- add explicit handling before "
                "resolving its schema."
            )

        return pa.decimal128(precision, scale)

    try:
        return _DATA_TYPE_TO_ARROW[data_type]
    except KeyError:
        raise ValueError(
            f"Column '{column_name}' has Postgres data_type "
            f"'{data_type}', which is not mapped to an Arrow type yet "
            "-- add it to _DATA_TYPE_TO_ARROW before resolving it."
        ) from None
