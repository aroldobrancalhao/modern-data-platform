"""
Modern Data Platform
Processing Framework

Integration tests for the Provider -> ComputeContextWriter ->
ProcessingContext chain (Fase 5 of the ADR-010 consolidation
roadmap).

Mirrors the pattern used by the Fase 4 BronzeIngestionStage
integration test, adapted to a ComputeProvider: an Execution is
produced by a fake, in-memory provider (no real Databricks client
involved) and published into the ProcessingContext by
ComputeContextWriter from within a Stage, executed end to end through
SequentialExecutor.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from data_platform.config.settings import Settings
from data_platform.contracts.compute_provider import ComputeProvider
from data_platform.models.compute import Execution, ExecutionStatus, Workload
from data_platform.processing.context_writers.compute_context_writer import (
    ComputeContextWriter,
)
from data_platform.processing.core.context_keys.compute_keys import (
    ComputeKeys,
)
from data_platform.processing.core.context_keys.processing_keys import (
    ProcessingKeys,
)
from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.execution_status import (
    ExecutionStatus as StageExecutionStatus,
)
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.pipeline_result import PipelineResult
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult
from data_platform.processing.executor.sequential_executor import (
    SequentialExecutor,
)
from data_platform.providers.provider_builder import ProviderBuilder
from data_platform.providers.provider_factory import ProviderFactory
from data_platform.providers.provider_registry import ProviderRegistry

pytestmark = pytest.mark.anyio


# ----------------------------------------------------------------------
# Test doubles
# ----------------------------------------------------------------------


class FakeComputeProvider(ComputeProvider):
    """
    Minimal in-memory implementation of the ComputeProvider contract,
    used to prove the ADR-010 execution chain closes end to end
    without depending on a real Databricks client.
    """

    def execute(self, workload: Workload) -> Execution:
        return Execution(
            execution_id=f"execution-for-{workload.identifier}",
            status=ExecutionStatus.RUNNING,
        )


class FakeComputeProviderBuilder(ProviderBuilder[FakeComputeProvider]):
    def build(self) -> FakeComputeProvider:
        return FakeComputeProvider()


@dataclass(eq=False, slots=True, kw_only=True)
class ComputeExecutionStage(Stage):
    """
    Minimal concrete Stage used only to prove that an Execution
    obtained from a ComputeProvider (resolved through the Stage's
    ProviderFactory) is correctly published into the
    ProcessingContext by ComputeContextWriter.
    """

    provider_name: str

    workload: Workload

    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:

        provider = self.resolve_provider(self.provider_name)
        assert isinstance(provider, ComputeProvider)

        execution = provider.execute(self.workload)

        ComputeContextWriter.write(self.workload, execution, context)

        return StageResult(
            status=StageExecutionStatus.COMPLETED,
            metadata=context.metadata,
            stage_id=self.id,
            stage_name=self.name,
        )


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-1",
        metadata=ExecutionMetadata(execution_id="execution-1"),
    )


def create_provider_factory() -> ProviderFactory:
    registry = ProviderRegistry()

    registry.register("databricks", FakeComputeProviderBuilder)

    return ProviderFactory(
        registry=registry,
        settings=Settings(),
    )


# ----------------------------------------------------------------------
# Scenario
# ----------------------------------------------------------------------


async def test_execution_is_published_into_the_processing_context() -> None:
    workload = Workload(identifier="silver-transform-customers")

    stage = ComputeExecutionStage(
        id="run-silver-transform",
        name="Run Silver Transform",
        provider_name="databricks",
        workload=workload,
        provider_factory=create_provider_factory(),
    )

    pipeline = Pipeline(
        id="compute-execution",
        name="Compute Execution",
        stages=(stage,),
    )

    context = create_context()

    result = await SequentialExecutor().execute(pipeline, context)

    assert result.status == StageExecutionStatus.COMPLETED
    assert result.total_stages == 1

    assert context.get(ComputeKeys.JOB_ID) == "silver-transform-customers"
    assert context.get(ComputeKeys.RUN_ID) == (
        "execution-for-silver-transform-customers"
    )

    pipeline_result = context.get(ProcessingKeys.PIPELINE_RESULT)
    assert isinstance(pipeline_result, PipelineResult)
    assert pipeline_result is result
    assert pipeline_result.status == StageExecutionStatus.COMPLETED
