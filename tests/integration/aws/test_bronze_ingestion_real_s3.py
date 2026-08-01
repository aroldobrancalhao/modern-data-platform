"""
Modern Data Platform
Processing Framework

Real-AWS smoke test for BronzeIngestionStage.

Proves the ADR-010 execution chain closes end to end against the
actual provisioned S3 bucket (mdp-datalake-dev-857854758128,
sa-east-1) and a real S3StorageProvider -- not the FakeStorageProvider
used by the Fase 4 integration test.

Requires valid AWS credentials and network access, so it is excluded
from the default suite (see `addopts = -m "not real_aws"` in
pyproject.toml). Run it explicitly with:

    uv run pytest tests/integration/aws/test_bronze_ingestion_real_s3.py -m real_aws -v

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import io
import uuid
from collections.abc import Iterator
from typing import cast

import pytest

from data_platform.bootstrap import bootstrap
from data_platform.config.settings import Settings
from data_platform.processing.bronze.bronze_ingestion_stage import (
    BronzeIngestionStage,
)
from data_platform.processing.core.context_keys.processing_keys import (
    ProcessingKeys,
)
from data_platform.processing.core.context_keys.storage_keys import (
    StorageKeys,
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
from data_platform.providers.provider_factory import ProviderFactory
from data_platform.storage.config import StorageSettings
from data_platform.storage.models import StorageLocation
from data_platform.storage.storage_provider import StorageProvider

pytestmark = [pytest.mark.anyio, pytest.mark.real_aws]

BUCKET = StorageSettings().default_bucket


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
def location(
    storage_provider: StorageProvider,
) -> Iterator[StorageLocation]:
    smoke_test_location = StorageLocation(
        scheme="s3",
        bucket=BUCKET,
        key=f"bronze/_smoke_test/{uuid.uuid4()}.txt",
    )

    try:
        yield smoke_test_location
    finally:
        storage_provider.delete(smoke_test_location)


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-real-s3-smoke-test",
        metadata=ExecutionMetadata(
            execution_id="execution-real-s3-smoke-test",
        ),
    )


async def test_bronze_ingestion_stage_against_real_s3(
    storage_provider: StorageProvider,
    provider_factory: ProviderFactory,
    location: StorageLocation,
) -> None:
    storage_provider.upload(
        location,
        io.BytesIO(b"bronze ingestion real-S3 smoke test\n"),
    )

    stage = BronzeIngestionStage(
        id="ingest-smoke-test",
        name="Ingest Smoke Test",
        provider_name="aws.s3",
        location=location,
        provider_factory=provider_factory,
    )

    pipeline = Pipeline(
        id="bronze-smoke-test",
        name="Bronze Smoke Test",
        stages=(stage,),
    )

    context = create_context()

    result = await SequentialExecutor().execute(pipeline, context)

    assert result.status == ExecutionStatus.COMPLETED
    assert context.get(StorageKeys.URI) == location.uri

    pipeline_result = context.get(ProcessingKeys.PIPELINE_RESULT)
    assert isinstance(pipeline_result, PipelineResult)
    assert pipeline_result is result
    assert pipeline_result.status == ExecutionStatus.COMPLETED
