"""
Modern Data Platform
Processing Framework

Unit tests for CatalogContextWriter.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.catalog.models import CatalogDatabase, CatalogTable
from data_platform.processing.context_writers.catalog_context_writer import (
    CatalogContextWriter,
)
from data_platform.processing.core.context_keys.catalog_keys import (
    CatalogKeys,
)
from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.storage.models import StorageLocation


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-1",
        metadata=ExecutionMetadata(execution_id="execution-1"),
    )


def test_write_database_populates_database_key() -> None:
    context = create_context()

    database = CatalogDatabase(name="bronze")

    CatalogContextWriter.write_database(database, context)

    assert context.get(CatalogKeys.DATABASE) == "bronze"


def test_write_table_populates_database_and_table_keys() -> None:
    context = create_context()

    table = CatalogTable(
        database="bronze",
        name="customers",
        location=StorageLocation(
            scheme="s3",
            bucket="bronze",
            key="customers/",
        ),
        columns=[],
    )

    CatalogContextWriter.write_table(table, context)

    assert context.get(CatalogKeys.DATABASE) == "bronze"
    assert context.get(CatalogKeys.TABLE) == "customers"


def test_write_table_never_sets_catalog_schema_or_view() -> None:
    context = create_context()

    table = CatalogTable(
        database="bronze",
        name="customers",
        location=StorageLocation(
            scheme="s3",
            bucket="bronze",
            key="customers/",
        ),
        columns=[],
    )

    CatalogContextWriter.write_table(table, context)

    assert context.contains(CatalogKeys.CATALOG) is False
    assert context.contains(CatalogKeys.SCHEMA) is False
    assert context.contains(CatalogKeys.VIEW) is False