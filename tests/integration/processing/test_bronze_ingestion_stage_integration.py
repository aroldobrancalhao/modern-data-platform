"""
Modern Data Platform
Processing Framework

Integration tests for BronzeIngestionStage (Fase 4 of the ADR-010
consolidation roadmap: the first concrete Stage proving that the
execution chain closes end to end):

    SequentialExecutor -> ExecutionRuntime -> ProcessingContext
        -> Stage.execute()
            -> Stage.resolve_provider() -> ProviderFactory/Registry
            -> StorageProvider (S3, via aws.s3)
            -> StorageContextWriter -> ProcessingContext / StorageKeys
        -> StageResult -> PipelineResult -> ProcessingContext

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, Iterable

import pytest

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
from data_platform.providers.provider import Provider
from data_platform.providers.provider_builder import ProviderBuilder
from data_platform.providers.provider_factory import ProviderFactory
from data_platform.providers.provider_registry import ProviderRegistry
from data_platform.storage.models import (
    StorageLocation,
    StorageMetadata,
    StorageObject,
)
from data_platform.storage.storage_provider import StorageProvider

pytestmark = pytest.mark.anyio


# ----------------------------------------------------------------------
# Test doubles
# ----------------------------------------------------------------------


class FakeStorageProvider(Provider, StorageProvider):
    """
    Minimal in-memory implementation of the StorageProvider contract,
    used to prove the ADR-010 execution chain closes end to end
    without depending on boto3 or any real AWS credentials.

    Mixes in Provider (like the real S3StorageProvider mixes in
    BaseProvider) so it satisfies ProviderBuilder's ``ProviderT``
    bound.
    """

    def __init__(
        self,
        objects: dict[str, StorageObject] | None = None,
    ) -> None:
        self._objects = objects if objects is not None else {}

    def exists(self, location: StorageLocation) -> bool:
        return location.uri in self._objects

    def upload(
        self,
        location: StorageLocation,
        source: Path | BinaryIO,
    ) -> None:
        self._objects[location.uri] = StorageObject(location=location)

    def download(
        self,
        location: StorageLocation,
        destination: Path,
    ) -> None:
        raise NotImplementedError

    def delete(self, location: StorageLocation) -> None:
        self._objects.pop(location.uri, None)

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
        return list(self._objects.values())

    def head(self, location: StorageLocation) -> StorageObject:
        return self._objects[location.uri]


class FakeStorageProviderBuilder(ProviderBuilder[FakeStorageProvider]):
    """
    Builds a FakeStorageProvider pre-populated with a single object,
    mimicking a landing bucket that already contains a file.
    """

    def build(self) -> FakeStorageProvider:
        location = StorageLocation(
            scheme="s3",
            bucket="bronze",
            key="customers/file.parquet",
        )

        return FakeStorageProvider(
            objects={
                location.uri: StorageObject(
                    location=location,
                    metadata=StorageMetadata(etag="fake-etag"),
                ),
            }
        )


class EmptyFakeStorageProviderBuilder(
    ProviderBuilder[FakeStorageProvider]
):
    """Builds a FakeStorageProvider with no objects at all."""

    def build(self) -> FakeStorageProvider:
        return FakeStorageProvider()


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-1",
        metadata=ExecutionMetadata(execution_id="execution-1"),
    )


def create_pipeline(stage: BronzeIngestionStage) -> Pipeline:
    return Pipeline(
        id="bronze-ingestion",
        name="Bronze Ingestion",
        stages=(stage,),
    )


def create_provider_factory(
    builder_type: type[ProviderBuilder],
) -> ProviderFactory:
    registry = ProviderRegistry()

    registry.register("aws.s3", builder_type)

    return ProviderFactory(
        registry=registry,
        settings=Settings(),
    )


# ----------------------------------------------------------------------
# Scenarios
# ----------------------------------------------------------------------


async def test_ingestion_succeeds_and_publishes_storage_and_pipeline_result() -> None:
    location = StorageLocation(
        scheme="s3",
        bucket="bronze",
        key="customers/file.parquet",
    )

    stage = BronzeIngestionStage(
        id="ingest-customers",
        name="Ingest Customers",
        provider_name="aws.s3",
        location=location,
        provider_factory=create_provider_factory(
            FakeStorageProviderBuilder,
        ),
    )

    context = create_context()

    result = await SequentialExecutor().execute(
        create_pipeline(stage),
        context,
    )

    assert result.status == ExecutionStatus.COMPLETED
    assert result.total_stages == 1
    assert result.stage_results[0].status == ExecutionStatus.COMPLETED

    assert context.get(StorageKeys.URI) == location.uri
    assert context.get(StorageKeys.BUCKET) == "bronze"
    assert context.get(StorageKeys.OBJECT_KEY) == "customers/file.parquet"
    assert context.get(StorageKeys.ETAG) == "fake-etag"

    pipeline_result = context.get(ProcessingKeys.PIPELINE_RESULT)
    assert isinstance(pipeline_result, PipelineResult)
    assert pipeline_result is result
    assert pipeline_result.status == ExecutionStatus.COMPLETED


async def test_missing_object_fails_as_a_business_failure_without_publishing_storage_keys() -> None:
    location = StorageLocation(
        scheme="s3",
        bucket="bronze",
        key="customers/missing.parquet",
    )

    stage = BronzeIngestionStage(
        id="ingest-customers",
        name="Ingest Customers",
        provider_name="aws.s3",
        location=location,
        provider_factory=create_provider_factory(
            EmptyFakeStorageProviderBuilder,
        ),
    )

    context = create_context()

    result = await SequentialExecutor().execute(
        create_pipeline(stage),
        context,
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.total_stages == 1

    stage_result = result.stage_results[0]
    assert stage_result.status == ExecutionStatus.FAILED
    assert stage_result.error_type == "ObjectNotFoundError"

    assert not context.contains(StorageKeys.URI)

    pipeline_result = context.get(ProcessingKeys.PIPELINE_RESULT)
    assert isinstance(pipeline_result, PipelineResult)
    assert pipeline_result.status == ExecutionStatus.FAILED


async def test_resolve_provider_raises_when_no_factory_was_injected() -> None:
    location = StorageLocation(
        scheme="s3",
        bucket="bronze",
        key="customers/file.parquet",
    )

    stage = BronzeIngestionStage(
        id="ingest-customers",
        name="Ingest Customers",
        provider_name="aws.s3",
        location=location,
    )

    with pytest.raises(RuntimeError, match="no ProviderFactory"):
        stage.resolve_provider(stage.provider_name)
