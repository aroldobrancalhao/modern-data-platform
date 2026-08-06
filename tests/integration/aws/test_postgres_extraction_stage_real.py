"""
Modern Data Platform
Processing Framework

Real-AWS smoke test for PostgresExtractionStage.

Proves the extraction chain closes end to end: a real local Postgres
table (docker compose, ``marketplace.customers``) is read via psycopg,
serialized to Parquet in memory, and landed in the actual provisioned
S3 bucket (mdp-datalake-dev-857854758128, sa-east-1) through a real
S3StorageProvider -- not a fake.

Postgres is always local (docker compose), so it needs no marker of
its own here. S3 is real, so this reuses `real_aws`, excluded from the
default suite. Run it explicitly with:

    uv run pytest tests/integration/aws/test_postgres_extraction_stage_real.py -m real_aws -v

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from typing import cast

import pytest

from data_platform.bootstrap import bootstrap
from data_platform.config.settings import Settings
from data_platform.processing.core.context_keys.processing_keys import (
    ProcessingKeys,
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
from data_platform.processing.executor.sequential_executor import (
    SequentialExecutor,
)
from data_platform.processing.extraction.postgres_extraction_stage import (
    PostgresExtractionStage,
)
from data_platform.providers.provider_factory import ProviderFactory
from data_platform.storage.config import StorageConfig
from data_platform.storage.models import StorageLocation
from data_platform.storage.storage_provider import StorageProvider

from integrations.postgres.config import PostgresSettings

pytestmark = [pytest.mark.anyio, pytest.mark.real_aws]

ENTITY = "customers"


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


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-real-postgres-extraction-smoke-test",
        metadata=ExecutionMetadata(
            execution_id="execution-real-postgres-extraction-smoke-test",
        ),
    )


async def test_postgres_extraction_stage_lands_raw_parquet_in_s3(
    storage_provider: StorageProvider,
    provider_factory: ProviderFactory,
) -> None:
    stage = PostgresExtractionStage(
        id="extract-customers",
        name="Extract Customers",
        provider_name="aws.s3",
        postgres_settings=PostgresSettings(),
        table_name="marketplace.customers",
        entity=ENTITY,
        provider_factory=provider_factory,
    )

    pipeline = Pipeline(
        id="postgres-extraction-smoke-test",
        name="Postgres Extraction Smoke Test",
        stages=(stage,),
    )

    context = create_context()

    uploaded_uri: str | None = None

    try:
        result = await SequentialExecutor().execute(pipeline, context)

        assert result.status == ExecutionStatus.COMPLETED

        uploaded_uri = result.stage_results[0].output["uri"]
        assert uploaded_uri is not None
        assert uploaded_uri.startswith(f"{StorageConfig.raw(ENTITY)}/")
        assert uploaded_uri.endswith(".parquet")

        location = StorageLocation.from_uri(uploaded_uri)
        assert storage_provider.exists(location)

        pipeline_result = context.get(ProcessingKeys.PIPELINE_RESULT)
        assert isinstance(pipeline_result, PipelineResult)
        assert pipeline_result is result
        assert pipeline_result.status == ExecutionStatus.COMPLETED

    finally:
        if uploaded_uri is not None:
            storage_provider.delete(StorageLocation.from_uri(uploaded_uri))
