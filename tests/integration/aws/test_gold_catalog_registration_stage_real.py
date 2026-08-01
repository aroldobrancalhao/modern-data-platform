"""
Modern Data Platform
Processing Framework

Real-AWS smoke test for GoldCatalogRegistrationStage.

Proves the Stage closes end to end against the actual provisioned
Glue database (mdp_gold_dev, sa-east-1) and a real S3StorageProvider/
GlueCatalogProvider -- not fakes.

Writing a Delta table directly to `s3://` via local Spark would need
the hadoop-aws/aws-java-sdk-bundle JARs (not installed) plus a
separate S3A credential setup -- out of scope just for this test.
Instead, `write_delta` writes a small real Delta table to a local
tmp_path (plain local Spark, already proven), and only its
`_delta_log/*.json` commit files get uploaded to the real bucket via
the real S3StorageProvider.upload() -- enough to exercise the Stage's
actual list()/download() calls against real S3 and create_table
against real Glue, without touching Spark/S3 wiring at all.

Needs BOTH `real_aws` (S3 + Glue) and `spark_local` (boots a real
local SparkSession just to produce a realistic _delta_log). Run it
manually, same discipline as the other spark_local tests -- stop the
local docker compose stack first (WSL memory pressure/OOM risk):

    docker compose -f infrastructure/docker/docker-compose.yml stop
    uv run pytest tests/integration/aws/test_gold_catalog_registration_stage_real.py -m "real_aws and spark_local" -v

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest
from pyspark.sql import Row, SparkSession

from data_platform.bootstrap import bootstrap
from data_platform.catalog import CatalogProvider
from data_platform.compute.delta_io import write_delta
from data_platform.compute.spark import get_spark
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
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.pipeline_result import PipelineResult
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.core.context_keys.processing_keys import (
    ProcessingKeys,
)
from data_platform.processing.executor.sequential_executor import (
    SequentialExecutor,
)
from data_platform.providers.provider_factory import ProviderFactory
from data_platform.storage.config import StorageConfig, StorageSettings
from data_platform.storage.models import StorageLocation
from data_platform.storage.storage_provider import StorageProvider

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.real_aws,
    pytest.mark.spark_local,
]

DATABASE = "mdp_gold_dev"
BUCKET = StorageSettings().default_bucket


@pytest.fixture(scope="module")
def spark() -> Iterator[SparkSession]:
    session = get_spark("gold-catalog-registration-real-aws-test")

    try:
        yield session
    finally:
        session.stop()


@pytest.fixture
def provider_factory() -> ProviderFactory:
    return ProviderFactory(
        registry=bootstrap(),
        settings=Settings(),
    )


@pytest.fixture
def storage_provider(
    provider_factory: ProviderFactory,
) -> StorageProvider:
    return cast(
        StorageProvider,
        provider_factory.create("aws.s3"),
    )


@pytest.fixture
def catalog_provider(
    provider_factory: ProviderFactory,
) -> CatalogProvider:
    return cast(
        CatalogProvider,
        provider_factory.create("aws.glue"),
    )


@pytest.fixture
def entity(
    spark: SparkSession,
    storage_provider: StorageProvider,
    tmp_path: Path,
) -> Iterator[str]:
    """
    Writes a small real Delta table locally, then uploads only its
    _delta_log/*.json commit files to the real Gold prefix for this
    smoke test's entity -- see module docstring for why.
    """

    entity_name = f"_smoke_test_{uuid.uuid4().hex}"

    local_path = tmp_path / "gold_table"

    df = spark.createDataFrame(
        [
            Row(customer_id=1, name="alice"),
            Row(customer_id=2, name="bob"),
        ]
    )

    write_delta(df, str(local_path), mode="overwrite")

    gold_location = StorageLocation.from_uri(
        StorageConfig.gold(entity_name)
    )

    uploaded_keys: list[str] = []

    for commit_file in sorted((local_path / "_delta_log").glob("*.json")):
        location = StorageLocation(
            scheme=gold_location.scheme,
            bucket=gold_location.bucket,
            key=f"{gold_location.key}/_delta_log/{commit_file.name}",
        )
        storage_provider.upload(location, commit_file)
        uploaded_keys.append(location.key)

    try:
        yield entity_name
    finally:
        for key in uploaded_keys:
            storage_provider.delete(
                StorageLocation(
                    scheme=gold_location.scheme,
                    bucket=gold_location.bucket,
                    key=key,
                )
            )


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-real-gold-catalog-registration",
        metadata=ExecutionMetadata(
            execution_id="execution-real-gold-catalog-registration",
        ),
    )


async def test_gold_delta_table_is_registered_in_the_real_glue_catalog(
    catalog_provider: CatalogProvider,
    provider_factory: ProviderFactory,
    entity: str,
) -> None:
    stage = GoldCatalogRegistrationStage(
        id="register-gold-smoke-test",
        name="Register Gold Smoke Test",
        storage_provider_name="aws.s3",
        catalog_provider_name="aws.glue",
        entity=entity,
        database=DATABASE,
        provider_factory=provider_factory,
    )

    pipeline = Pipeline(
        id="gold-catalog-registration-smoke-test",
        name="Gold Catalog Registration Smoke Test",
        stages=(stage,),
    )

    context = create_context()

    try:
        result = await SequentialExecutor().execute(pipeline, context)

        assert result.status == ExecutionStatus.COMPLETED

        assert context.get(CatalogKeys.DATABASE) == DATABASE
        assert context.get(CatalogKeys.TABLE) == entity

        pipeline_result = context.get(ProcessingKeys.PIPELINE_RESULT)
        assert isinstance(pipeline_result, PipelineResult)
        assert pipeline_result is result
        assert pipeline_result.status == ExecutionStatus.COMPLETED

        persisted = catalog_provider.get_table(DATABASE, entity)
        assert persisted.name == entity
        assert [
            (column.name, column.type) for column in persisted.columns
        ] == [
            ("customer_id", "bigint"),
            ("name", "string"),
        ]

    finally:
        if catalog_provider.table_exists(DATABASE, entity):
            catalog_provider.delete_table(DATABASE, entity)
