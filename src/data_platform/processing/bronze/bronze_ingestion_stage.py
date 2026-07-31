"""
Modern Data Platform
Processing Framework

Bronze ingestion stage.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from data_platform.processing.context_writers.storage_context_writer import (
    StorageContextWriter,
)
from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult
from data_platform.storage.models import StorageLocation
from data_platform.storage.storage_error import ObjectNotFoundError
from data_platform.storage.storage_provider import StorageProvider


@dataclass(eq=False, slots=True, kw_only=True)
class BronzeIngestionStage(Stage):
    """
    Ingests a single object from a landing/bronze storage location.

    Resolves a StorageProvider through the Stage's ProviderFactory,
    confirms the source object exists and publishes its location (and
    metadata, when available) into the ProcessingContext through
    StorageContextWriter.

    A missing object is treated as a business failure -- a retry will
    not make it appear -- so it is reported through a FAILED
    StageResult for FailurePolicy to handle, instead of being raised.
    Any other StorageError (e.g. connectivity issues) is left to
    propagate, so RetryPolicy can act on it.
    """

    provider_name: str

    location: StorageLocation

    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:

        provider = cast(
            StorageProvider,
            self.resolve_provider(self.provider_name),
        )

        if not provider.exists(self.location):
            return StageResult(
                status=ExecutionStatus.FAILED,
                metadata=context.metadata,
                stage_id=self.id,
                stage_name=self.name,
                error_type=ObjectNotFoundError.__name__,
                error_message=(
                    f"Object not found at '{self.location.uri}'."
                ),
            )

        storage_object = provider.head(self.location)

        StorageContextWriter.write(
            self.location,
            context,
            storage_object=storage_object,
        )

        return StageResult(
            status=ExecutionStatus.COMPLETED,
            metadata=context.metadata,
            stage_id=self.id,
            stage_name=self.name,
        )
