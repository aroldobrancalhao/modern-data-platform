"""
Modern Data Platform
Processing Framework

Unit tests for PostgresExtractionStage's schema resolution.

Regression coverage for a real bug: _extract() used to build the
Arrow schema purely from the values pyarrow.table() saw, so a
zero-row extraction produced an all-``null`` schema. Landing an empty
snapshot and a later, populated one under the same raw/{entity}/
prefix gave Spark two Parquet files with incompatible physical types
for the same logical column (e.g. a uuid column: ``null`` in the
empty file, ``FIXED_LEN_BYTE_ARRAY`` in the populated one) --
confirmed against the real Databricks failure this fixes.

These tests use a fake connection/cursor (no real Postgres) so the
schema resolution can be proven with zero rows deterministically,
without depending on any table actually being empty.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pytest

from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.extraction.postgres_extraction_stage import (
    PostgresExtractionStage,
    _arrow_type_for_column,
)
from data_platform.providers.provider_factory import ProviderFactory

from integrations.postgres.config import PostgresSettings

pytestmark = pytest.mark.anyio


@dataclass
class _FakeColumn:
    """Duck-types the subset of psycopg.Column that _extract() reads."""

    name: str
    type_code: int
    precision: int | None = None
    scale: int | None = None


class _FakeCursor:
    def __init__(self, description: list[_FakeColumn], rows: list) -> None:
        self.description = description
        self._rows = rows

    def execute(self, *args: object, **kwargs: object) -> None:
        pass

    def fetchall(self) -> list:
        return self._rows

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *args: object) -> None:
        pass


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def cursor(self) -> _FakeCursor:
        return self._cursor

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, *args: object) -> None:
        pass


def _stage() -> PostgresExtractionStage:
    return PostgresExtractionStage(
        id="extract-customers",
        name="Extract Customers",
        provider_name="aws.s3",
        postgres_settings=PostgresSettings(),
        table_name="marketplace.customers",
        entity="customers",
    )


def test_uuid_column_keeps_its_type_with_zero_rows() -> None:
    """
    uuid columns are typed pa.string(), not pa.uuid(): Spark's Parquet
    reader rejects the UUID logical type outright
    ([PARQUET_TYPE_ILLEGAL] Illegal Parquet type: FIXED_LEN_BYTE_ARRAY
    (UUID)), confirmed against a real Databricks run. The regression
    this guards against is unchanged -- a zero-row extraction must
    still produce a real, non-null type for this column.
    """
    description = [_FakeColumn(name="customer_id", type_code=2950)]

    with patch(
        "data_platform.processing.extraction.postgres_extraction_stage.psycopg.connect",
        return_value=_FakeConnection(_FakeCursor(description, rows=[])),
    ):
        table = _stage()._extract()

    assert table.num_rows == 0
    assert table.schema.field("customer_id").type == pa.string()


def test_uuid_values_are_stringified() -> None:
    """
    psycopg returns uuid columns as uuid.UUID objects, but the schema
    types them pa.string() -- pyarrow does not coerce UUID objects
    into strings on its own (raises "Expected bytes, got a 'UUID'
    object" if handed one directly), so _extract() has to do it.
    """
    description = [_FakeColumn(name="customer_id", type_code=2950)]
    value = uuid.uuid4()

    with patch(
        "data_platform.processing.extraction.postgres_extraction_stage.psycopg.connect",
        return_value=_FakeConnection(
            _FakeCursor(description, rows=[(value,), (None,)])
        ),
    ):
        table = _stage()._extract()

    assert table.column("customer_id").to_pylist() == [str(value), None]


def test_numeric_column_becomes_a_decimal_with_the_real_precision_and_scale() -> (
    None
):
    description = [
        _FakeColumn(name="amount", type_code=1700, precision=19, scale=4)
    ]

    with patch(
        "data_platform.processing.extraction.postgres_extraction_stage.psycopg.connect",
        return_value=_FakeConnection(_FakeCursor(description, rows=[])),
    ):
        table = _stage()._extract()

    assert table.schema.field("amount").type == pa.decimal128(19, 4)


def test_arrow_type_for_column_raises_on_an_unmapped_type_oid() -> None:
    column = _FakeColumn(name="tags", type_code=9999)

    with pytest.raises(ValueError, match="not mapped to an Arrow type"):
        _arrow_type_for_column(column)  # type: ignore[arg-type]


def test_arrow_type_for_column_raises_on_numeric_without_precision() -> None:
    column = _FakeColumn(name="amount", type_code=1700)

    with pytest.raises(ValueError, match="without a precision/scale"):
        _arrow_type_for_column(column)  # type: ignore[arg-type]


async def test_execute_returns_the_landed_location_on_output() -> None:
    """
    Regression coverage for the ParallelExecutor migration: execute()
    used to publish the landed location into the shared
    ProcessingContext via StorageContextWriter -- unsafe if this Stage
    ever runs inside a parallel group (see ParallelExecutor's
    docstring). It now returns it on StageResult.output instead,
    which a coroutine's own return value can't collide on.
    """

    description = [_FakeColumn(name="customer_id", type_code=2950)]

    fake_provider = MagicMock()

    provider_factory = MagicMock(spec=ProviderFactory)
    provider_factory.create.return_value = fake_provider

    stage = PostgresExtractionStage(
        id="extract-customers",
        name="Extract Customers",
        provider_name="aws.s3",
        postgres_settings=PostgresSettings(),
        table_name="marketplace.customers",
        entity="customers",
        provider_factory=provider_factory,
    )

    context = ProcessingContext(
        id="context",
        metadata=ExecutionMetadata(execution_id="execution"),
    )

    with patch(
        "data_platform.processing.extraction.postgres_extraction_stage.psycopg.connect",
        return_value=_FakeConnection(_FakeCursor(description, rows=[])),
    ):
        result = await stage.execute(context)

    assert result.succeeded

    fake_provider.upload.assert_called_once()

    uploaded_location = fake_provider.upload.call_args[0][0]

    assert result.output["uri"] == uploaded_location.uri
    assert result.output["bucket"] == uploaded_location.bucket
    assert result.output["object_key"] == uploaded_location.key
    assert result.output["uri"].startswith("s3://")
    assert "/raw/customers/" in result.output["uri"]
    assert result.output["uri"].endswith(".parquet")
