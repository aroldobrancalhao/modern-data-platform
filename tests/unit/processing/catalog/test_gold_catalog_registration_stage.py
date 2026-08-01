"""
Modern Data Platform
Processing Framework

Unit tests for GoldCatalogRegistrationStage: proves the Delta
_delta_log scanning logic (including the "scan backwards until a
metaData action is found" rule, confirmed empirically against a real
local Delta table) and the Spark -> Glue type mapping, entirely with
in-memory fakes -- no real S3/Glue, no Spark.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import BinaryIO, Iterable

import pytest

from data_platform.catalog import CatalogDatabase, CatalogTable
from data_platform.config.settings import Settings
from data_platform.processing.catalog.gold_catalog_registration_stage import (
    GoldCatalogRegistrationStage,
)
from data_platform.processing.core.context_keys.catalog_keys import (
    CatalogKeys,
)
from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.catalog.catalog_provider import CatalogProvider
from data_platform.providers.provider import Provider
from data_platform.providers.provider_builder import ProviderBuilder
from data_platform.providers.provider_factory import ProviderFactory
from data_platform.providers.provider_registry import ProviderRegistry
from data_platform.storage.models import StorageLocation, StorageObject
from data_platform.storage.storage_provider import StorageProvider

pytestmark = pytest.mark.anyio

BUCKET = "mdp-datalake-dev-857854758128"
ENTITY = "customers"
DATABASE = "mdp_gold_dev"


# ----------------------------------------------------------------------
# Test doubles
# ----------------------------------------------------------------------


class FakeStorageProvider(Provider, StorageProvider):
    """
    In-memory StorageProvider backed by a flat {key: bytes} mapping --
    just enough to exercise list()/download() against a fake
    _delta_log, without any real S3.
    """

    def __init__(self, files: dict[str, bytes]) -> None:
        self._files = files

    def exists(self, location: StorageLocation) -> bool:
        return location.key in self._files

    def upload(
        self,
        location: StorageLocation,
        source: Path | BinaryIO,
    ) -> None:
        raise NotImplementedError

    def download(
        self,
        location: StorageLocation,
        destination: Path,
    ) -> None:
        destination.write_bytes(self._files[location.key])

    def delete(self, location: StorageLocation) -> None:
        raise NotImplementedError

    def copy(
        self,
        source: StorageLocation,
        destination: StorageLocation,
    ) -> None:
        raise NotImplementedError

    def move(
        self,
        source: StorageLocation,
        destination: StorageLocation,
    ) -> None:
        raise NotImplementedError

    def list(
        self,
        location: StorageLocation,
    ) -> Iterable[StorageObject]:
        return [
            StorageObject(
                location=StorageLocation(
                    scheme=location.scheme,
                    bucket=location.bucket,
                    key=key,
                )
            )
            for key in self._files
            if key.startswith(location.key)
        ]

    def head(self, location: StorageLocation) -> StorageObject:
        raise NotImplementedError


class FakeCatalogProvider(Provider, CatalogProvider):
    """
    In-memory CatalogProvider that only implements create_table --
    the only method GoldCatalogRegistrationStage actually calls.
    """

    def __init__(self) -> None:
        self.created_tables: list[CatalogTable] = []

    def database_exists(self, database: str) -> bool:
        raise NotImplementedError

    def create_database(self, database: CatalogDatabase) -> None:
        raise NotImplementedError

    def delete_database(self, database: str) -> None:
        raise NotImplementedError

    def get_database(self, database: str) -> CatalogDatabase:
        raise NotImplementedError

    def list_databases(self) -> list[CatalogDatabase]:
        raise NotImplementedError

    def table_exists(self, database: str, table: str) -> bool:
        raise NotImplementedError

    def create_table(self, table: CatalogTable) -> None:
        self.created_tables.append(table)

    def delete_table(self, database: str, table: str) -> None:
        raise NotImplementedError

    def get_table(self, database: str, table: str) -> CatalogTable:
        raise NotImplementedError

    def list_tables(self, database: str) -> list[CatalogTable]:
        raise NotImplementedError

    def get_table_location(
        self, database: str, table: str
    ) -> StorageLocation:
        raise NotImplementedError

    def update_table_location(
        self,
        database: str,
        table: str,
        location: StorageLocation,
    ) -> None:
        raise NotImplementedError

    def repair_table(self, database: str, table: str) -> None:
        raise NotImplementedError


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _commit_line(action: dict) -> str:
    return json.dumps(action) + "\n"


def _metadata_action(fields: list[dict]) -> dict:
    return {
        "metaData": {
            "id": "fake-id",
            "schemaString": json.dumps(
                {"type": "struct", "fields": fields}
            ),
        }
    }


def _delta_log_key(version: int) -> str:
    return (
        f"gold/{ENTITY}/_delta_log/{version:020d}.json"
    )


def _build_stage(
    storage_provider: FakeStorageProvider,
    catalog_provider: FakeCatalogProvider,
) -> GoldCatalogRegistrationStage:
    registry = ProviderRegistry()

    class StorageBuilder(ProviderBuilder[FakeStorageProvider]):
        def build(self) -> FakeStorageProvider:
            return storage_provider

    class CatalogBuilder(ProviderBuilder[FakeCatalogProvider]):
        def build(self) -> FakeCatalogProvider:
            return catalog_provider

    registry.register("aws.s3", StorageBuilder)
    registry.register("aws.glue", CatalogBuilder)

    provider_factory = ProviderFactory(
        registry=registry,
        settings=Settings(),
    )

    return GoldCatalogRegistrationStage(
        id="register-gold-customers",
        name="Register Gold Customers",
        storage_provider_name="aws.s3",
        catalog_provider_name="aws.glue",
        entity=ENTITY,
        database=DATABASE,
        provider_factory=provider_factory,
    )


def _create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-gold-catalog-registration",
        metadata=ExecutionMetadata(
            execution_id="execution-gold-catalog-registration",
        ),
    )


# ----------------------------------------------------------------------
# Scenarios
# ----------------------------------------------------------------------


async def test_registers_the_table_and_publishes_catalog_context() -> None:
    files = {
        _delta_log_key(0): _commit_line(
            _metadata_action(
                [
                    {
                        "name": "customer_id",
                        "type": "long",
                        "nullable": True,
                        "metadata": {},
                    },
                    {
                        "name": "name",
                        "type": "string",
                        "nullable": True,
                        "metadata": {},
                    },
                ]
            )
        ).encode()
    }

    storage_provider = FakeStorageProvider(files)
    catalog_provider = FakeCatalogProvider()

    stage = _build_stage(storage_provider, catalog_provider)
    context = _create_context()

    result = await stage.execute(context)

    assert result.status == ExecutionStatus.COMPLETED

    assert len(catalog_provider.created_tables) == 1
    table = catalog_provider.created_tables[0]
    assert table.database == DATABASE
    assert table.name == ENTITY
    assert [(c.name, c.type) for c in table.columns] == [
        ("customer_id", "bigint"),
        ("name", "string"),
    ]
    assert table.table_format == "delta"

    assert context.get(CatalogKeys.DATABASE) == DATABASE
    assert context.get(CatalogKeys.TABLE) == ENTITY


async def test_scans_backwards_to_find_the_last_schema_change() -> None:
    """
    Mirrors what a second `write_delta(..., mode="overwrite")` with an
    unchanged schema really produces: the newest commit carries no
    metaData action at all, only the earlier one does.
    """

    files = {
        _delta_log_key(0): _commit_line(
            _metadata_action(
                [
                    {
                        "name": "customer_id",
                        "type": "long",
                        "nullable": True,
                        "metadata": {},
                    },
                ]
            )
        ).encode(),
        _delta_log_key(1): _commit_line(
            {"add": {"path": "part-00000.parquet"}}
        ).encode(),
    }

    storage_provider = FakeStorageProvider(files)
    catalog_provider = FakeCatalogProvider()

    stage = _build_stage(storage_provider, catalog_provider)
    context = _create_context()

    result = await stage.execute(context)

    assert result.status == ExecutionStatus.COMPLETED
    assert [
        c.name for c in catalog_provider.created_tables[0].columns
    ] == ["customer_id"]


async def test_missing_delta_table_fails_as_a_business_failure() -> None:
    storage_provider = FakeStorageProvider(files={})
    catalog_provider = FakeCatalogProvider()

    stage = _build_stage(storage_provider, catalog_provider)
    context = _create_context()

    result = await stage.execute(context)

    assert result.status == ExecutionStatus.FAILED
    assert result.error_type == "DeltaTableNotFoundError"
    assert catalog_provider.created_tables == []
    assert not context.contains(CatalogKeys.TABLE)


async def test_no_metadata_action_in_any_commit_raises() -> None:
    files = {
        _delta_log_key(0): _commit_line(
            {"add": {"path": "part-00000.parquet"}}
        ).encode(),
    }

    storage_provider = FakeStorageProvider(files)
    catalog_provider = FakeCatalogProvider()

    stage = _build_stage(storage_provider, catalog_provider)
    context = _create_context()

    with pytest.raises(RuntimeError, match="No metaData action"):
        await stage.execute(context)


async def test_unsupported_spark_type_raises() -> None:
    files = {
        _delta_log_key(0): _commit_line(
            _metadata_action(
                [
                    {
                        "name": "tags",
                        "type": {
                            "type": "array",
                            "elementType": "string",
                            "containsNull": True,
                        },
                        "nullable": True,
                        "metadata": {},
                    },
                ]
            )
        ).encode()
    }

    storage_provider = FakeStorageProvider(files)
    catalog_provider = FakeCatalogProvider()

    stage = _build_stage(storage_provider, catalog_provider)
    context = _create_context()

    with pytest.raises(ValueError, match="Unsupported Delta/Spark type"):
        await stage.execute(context)
