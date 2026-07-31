"""
Modern Data Platform
Processing Framework

Integration tests for the Provider -> WorkflowContextWriter ->
ProcessingContext chain (Fase 5 of the ADR-010 consolidation
roadmap).

Mirrors the pattern used by the Fase 4 BronzeIngestionStage
integration test, adapted to a WorkflowProvider: a WorkflowRun is
built by a fake, in-memory provider (no real Airflow client involved)
and published into the ProcessingContext by WorkflowContextWriter
from within a Stage, executed end to end through SequentialExecutor.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from data_platform.config.settings import Settings
from data_platform.contracts.workflow_provider import WorkflowProvider
from data_platform.processing.context_writers.workflow_context_writer import (
    WorkflowContextWriter,
)
from data_platform.processing.core.context_keys.processing_keys import (
    ProcessingKeys,
)
from data_platform.processing.core.context_keys.workflow_keys import (
    WorkflowKeys,
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
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult
from data_platform.processing.executor.sequential_executor import (
    SequentialExecutor,
)
from data_platform.providers.provider_builder import ProviderBuilder
from data_platform.providers.provider_factory import ProviderFactory
from data_platform.providers.provider_registry import ProviderRegistry
from data_platform.workflow.models import Workflow, WorkflowRun, WorkflowStatus

pytestmark = pytest.mark.anyio


# ----------------------------------------------------------------------
# Test doubles
# ----------------------------------------------------------------------


class FakeWorkflowProvider(WorkflowProvider):
    """
    Minimal in-memory implementation of the WorkflowProvider contract,
    used to prove the ADR-010 execution chain closes end to end
    without depending on a real Airflow client.
    """

    def list_workflows(self) -> list[Workflow]:
        raise NotImplementedError

    def get_workflow(self, workflow_id: str) -> Workflow:
        raise NotImplementedError

    def trigger(
        self,
        workflow_id: str,
        parameters: dict[str, object] | None = None,
    ) -> WorkflowRun:
        return WorkflowRun(
            run_id="run-1",
            workflow_id=workflow_id,
            workflow_name="Bronze Ingestion DAG",
            status=WorkflowStatus.RUNNING,
            parameters=parameters or {},
            metadata={
                "execution_url": "https://airflow.example.com/runs/run-1",
                "schedule_id": "schedule-1",
            },
        )

    def get_run(self, workflow_id: str, run_id: str) -> WorkflowRun:
        raise NotImplementedError

    def list_runs(self, workflow_id: str) -> list[WorkflowRun]:
        raise NotImplementedError

    def cancel(self, workflow_id: str, run_id: str) -> None:
        raise NotImplementedError


class FakeWorkflowProviderBuilder(ProviderBuilder[FakeWorkflowProvider]):
    def build(self) -> FakeWorkflowProvider:
        return FakeWorkflowProvider()


@dataclass(eq=False, slots=True, kw_only=True)
class WorkflowTriggerStage(Stage):
    """
    Minimal concrete Stage used only to prove that a WorkflowRun
    obtained from a WorkflowProvider (resolved through the Stage's
    ProviderFactory) is correctly published into the
    ProcessingContext by WorkflowContextWriter.
    """

    provider_name: str

    workflow_id: str

    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:

        provider = self.resolve_provider(self.provider_name)
        assert isinstance(provider, WorkflowProvider)

        run = provider.trigger(self.workflow_id)

        WorkflowContextWriter.write(run, context)

        return StageResult(
            status=ExecutionStatus.COMPLETED,
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

    registry.register("airflow", FakeWorkflowProviderBuilder)

    return ProviderFactory(
        registry=registry,
        settings=Settings(),
    )


# ----------------------------------------------------------------------
# Scenario
# ----------------------------------------------------------------------


async def test_workflow_run_is_published_into_the_processing_context() -> None:
    stage = WorkflowTriggerStage(
        id="trigger-bronze-dag",
        name="Trigger Bronze DAG",
        provider_name="airflow",
        workflow_id="dag-1",
        provider_factory=create_provider_factory(),
    )

    pipeline = Pipeline(
        id="workflow-trigger",
        name="Workflow Trigger",
        stages=(stage,),
    )

    context = create_context()

    result = await SequentialExecutor().execute(pipeline, context)

    assert result.status == ExecutionStatus.COMPLETED
    assert result.total_stages == 1

    assert context.get(WorkflowKeys.WORKFLOW_ID) == "dag-1"
    assert context.get(WorkflowKeys.WORKFLOW_NAME) == (
        "Bronze Ingestion DAG"
    )
    assert context.get(WorkflowKeys.RUN_ID) == "run-1"
    assert context.get(WorkflowKeys.EXECUTION_URL) == (
        "https://airflow.example.com/runs/run-1"
    )
    assert context.get(WorkflowKeys.SCHEDULE_ID) == "schedule-1"

    pipeline_result = context.get(ProcessingKeys.PIPELINE_RESULT)
    assert isinstance(pipeline_result, PipelineResult)
    assert pipeline_result is result
    assert pipeline_result.status == ExecutionStatus.COMPLETED
