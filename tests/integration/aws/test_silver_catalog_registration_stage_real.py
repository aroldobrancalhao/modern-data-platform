"""
Modern Data Platform
Processing Framework

Real-AWS smoke test for SilverCatalogRegistrationStage.

Proves the Stage closes end to end against the actual provisioned
Glue database (mdp_silver_dev, sa-east-1) and a real S3StorageProvider/
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
    uv run pytest tests/integration/aws/test_silver_catalog_registration_stage_real.py -m "real_aws and spark_local" -v

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import boto3
import pytest
from pyspark.sql import Row, SparkSession

from data_platform.bootstrap import bootstrap
from data_platform.catalog import CatalogProvider
from data_platform.compute.delta_io import write_delta
from data_platform.compute.spark import get_spark
from data_platform.config.settings import Settings
from data_platform.processing.catalog.silver_catalog_registration_stage import (
    SilverCatalogRegistrationStage,
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

DATABASE = "mdp_silver_dev"
BUCKET = StorageSettings().default_bucket


@pytest.fixture(scope="module")
def spark() -> Iterator[SparkSession]:
    session = get_spark("silver-catalog-registration-real-aws-test")

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
    _delta_log/*.json commit files to the real Silver prefix for this
    smoke test's entity -- see module docstring for why.
    """

    entity_name = f"_smoke_test_{uuid.uuid4().hex}"

    local_path = tmp_path / "silver_table"

    df = spark.createDataFrame(
        [
            Row(customer_id=1, name="alice"),
            Row(customer_id=2, name="bob"),
        ]
    )

    write_delta(df, str(local_path), mode="overwrite")

    silver_location = StorageLocation.from_uri(
        StorageConfig.silver(entity_name)
    )

    uploaded_keys: list[str] = []

    for commit_file in sorted((local_path / "_delta_log").glob("*.json")):
        location = StorageLocation(
            scheme=silver_location.scheme,
            bucket=silver_location.bucket,
            key=f"{silver_location.key}/_delta_log/{commit_file.name}",
        )
        storage_provider.upload(location, commit_file)
        uploaded_keys.append(location.key)

    try:
        yield entity_name
    finally:
        for key in uploaded_keys:
            storage_provider.delete(
                StorageLocation(
                    scheme=silver_location.scheme,
                    bucket=silver_location.bucket,
                    key=key,
                )
            )


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-real-silver-catalog-registration",
        metadata=ExecutionMetadata(
            execution_id="execution-real-silver-catalog-registration",
        ),
    )


async def test_silver_delta_table_is_registered_in_the_real_glue_catalog(
    catalog_provider: CatalogProvider,
    provider_factory: ProviderFactory,
    entity: str,
) -> None:
    stage = SilverCatalogRegistrationStage(
        id="register-silver-smoke-test",
        name="Register Silver Smoke Test",
        storage_provider_name="aws.s3",
        catalog_provider_name="aws.glue",
        entity=entity,
        database=DATABASE,
        provider_factory=provider_factory,
    )

    pipeline = Pipeline(
        id="silver-catalog-registration-smoke-test",
        name="Silver Catalog Registration Smoke Test",
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

        glue_table = boto3.client(
            "glue", region_name="sa-east-1"
        ).get_table(DatabaseName=DATABASE, Name=entity)["Table"]

        storage_descriptor = glue_table["StorageDescriptor"]
        assert storage_descriptor["InputFormat"] == (
            "org.apache.hadoop.mapred.SequenceFileInputFormat"
        )
        assert storage_descriptor["SerdeInfo"]["Parameters"]["path"] == (
            f"s3://{BUCKET}/silver/{entity}"
        )
        assert glue_table["Parameters"]["table_type"] == "DELTA"
        assert (
            glue_table["Parameters"]["spark.sql.sources.provider"]
            == "delta"
        )

    finally:
        if catalog_provider.table_exists(DATABASE, entity):
            catalog_provider.delete_table(DATABASE, entity)
