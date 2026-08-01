"""
Modern Data Platform

Unit tests for GlueCatalogProvider.create_table()'s storage format
branching.

Regression coverage for a real bug: create_table() used to hardcode
the text/CSV InputFormat/OutputFormat/SerDe for every table,
regardless of CatalogTable.table_format. A Delta table registered
that way still "succeeded" (CreateTable didn't error, and Athena
SELECT even returned rows) -- it just silently read the raw Parquet
bytes as newline-delimited text, so `SELECT count(*)` came back wrong
(1055 instead of the real 1000) instead of erroring. Confirmed against
real Glue/Athena before writing this fix (see
docs/architecture/roadmap-next-steps.md history / GoldCatalogRegistrationStage).

These tests use a fake Glue client (no real AWS) so the exact
TableInput built for both table_format values can be asserted
directly and fast.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from typing import Any

from data_platform.catalog.models import CatalogColumn, CatalogTable
from data_platform.storage.models import StorageLocation
from integrations.aws.catalog.glue_catalog_provider import (
    GlueCatalogProvider,
)


class _FakeEntityNotFoundException(Exception):
    pass


class _FakeExceptions:
    EntityNotFoundException = _FakeEntityNotFoundException


class _FakeGlueClient:
    """
    Only implements what create_table() calls: table_exists() (via
    get_table(), always "not found" here so create_table() proceeds)
    and create_table() itself, capturing the TableInput it was given.
    """

    def __init__(self) -> None:
        self.exceptions = _FakeExceptions()
        self.created_table_input: dict[str, Any] | None = None

    def get_table(self, DatabaseName: str, Name: str) -> None:
        raise self.exceptions.EntityNotFoundException()

    def create_table(
        self,
        DatabaseName: str,
        TableInput: dict[str, Any],
    ) -> None:
        self.created_table_input = TableInput


def _provider(client: _FakeGlueClient) -> GlueCatalogProvider:
    provider = GlueCatalogProvider.__new__(GlueCatalogProvider)
    provider._client = client  # type: ignore[attr-defined]
    return provider


def _table(table_format: str) -> CatalogTable:
    return CatalogTable(
        database="mdp_gold_dev",
        name="customers",
        location=StorageLocation(
            scheme="s3",
            bucket="mdp-datalake-dev-857854758128",
            key="gold/customers",
        ),
        columns=[CatalogColumn(name="customer_id", type="string")],
        table_format=table_format,
    )


def test_delta_table_gets_the_delta_storage_format_and_parameters() -> None:
    client = _FakeGlueClient()

    _provider(client).create_table(_table("delta"))

    assert client.created_table_input is not None
    storage_descriptor = client.created_table_input["StorageDescriptor"]

    assert storage_descriptor["InputFormat"] == (
        "org.apache.hadoop.mapred.SequenceFileInputFormat"
    )
    assert storage_descriptor["OutputFormat"] == (
        "org.apache.hadoop.hive.ql.io.HiveSequenceFileOutputFormat"
    )
    assert storage_descriptor["SerdeInfo"]["Parameters"] == {
        "serialization.format": "1",
        "path": "s3://mdp-datalake-dev-857854758128/gold/customers",
    }

    assert client.created_table_input["Parameters"] == {
        "table_type": "DELTA",
        "spark.sql.sources.provider": "delta",
    }


def test_generic_table_keeps_the_original_text_storage_format() -> None:
    client = _FakeGlueClient()

    _provider(client).create_table(_table("generic"))

    assert client.created_table_input is not None
    storage_descriptor = client.created_table_input["StorageDescriptor"]

    assert storage_descriptor["InputFormat"] == (
        "org.apache.hadoop.mapred.TextInputFormat"
    )
    assert storage_descriptor["OutputFormat"] == (
        "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"
    )
    assert "Parameters" not in storage_descriptor["SerdeInfo"]

    assert "Parameters" not in client.created_table_input


def test_table_format_defaults_to_generic() -> None:
    table = CatalogTable(
        database="db",
        name="table",
        location=StorageLocation(scheme="s3", bucket="b", key="k"),
        columns=[],
    )

    assert table.table_format == "generic"
