"""
Modern Data Platform
Processing Framework

Integration test for the Provider -> WorkflowContextWriter ->
ProcessingContext chain against a REAL Airflow instance (Fase 5 of the
ADR-010 consolidation roadmap).

test_workflow_context_writer_integration.py proves this chain with a
FakeWorkflowProvider; this test closes the loop with the real
AirflowWorkflowProvider, resolved through the real
bootstrap() -> ProviderFactory chain, against the local Airflow
container.

No pytest marker: follows the same convention already established by
tests/integration/airflow/test_workflow_provider.py -- those tests
assume the local docker compose stack (mdp-airflow-apiserver on
localhost:8080) is up, with no marker/skip-if-unreachable guard, and
this test depends on the exact same local infrastructure.

Triggers the existing, unpaused "platform_validation" placeholder DAG
(airflow/dags/foundation/platform_validation.py) -- it only reads an
Airflow Variable and asserts on it, no external side effects, so no
cleanup is needed after triggering a run. (The existing
test_workflow_provider.py tests already trigger this same DAG
unconditionally on every suite run.)

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from data_platform.bootstrap import bootstrap
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
from data_platform.providers.provider_factory import ProviderFactory

pytestmark = pytest.mark.anyio

WORKFLOW_ID = "platform_validation"


@dataclass(eq=False, slots=True, kw_only=True)
class WorkflowTriggerStage(Stage):
    """
    Minimal concrete Stage used only to prove that a WorkflowRun
    obtained from a real WorkflowProvider (resolved through the
    Stage's ProviderFactory) is correctly published into the
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


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-real-airflow",
        metadata=ExecutionMetadata(
            execution_id="execution-real-airflow",
        ),
    )


def create_provider_factory() -> ProviderFactory:
    return ProviderFactory(
        registry=bootstrap(),
        settings=Settings(),
    )


async def test_workflow_run_is_published_into_the_processing_context() -> None:
    stage = WorkflowTriggerStage(
        id="trigger-platform-validation",
        name="Trigger Platform Validation",
        provider_name="airflow",
        workflow_id=WORKFLOW_ID,
        provider_factory=create_provider_factory(),
    )

    pipeline = Pipeline(
        id="workflow-trigger-real-airflow",
        name="Workflow Trigger (real Airflow)",
        stages=(stage,),
    )

    context = create_context()

    result = await SequentialExecutor().execute(pipeline, context)

    assert result.status == ExecutionStatus.COMPLETED
    assert result.total_stages == 1

    assert context.get(WorkflowKeys.WORKFLOW_ID) == WORKFLOW_ID
    assert context.get(WorkflowKeys.RUN_ID) is not None

    pipeline_result = context.get(ProcessingKeys.PIPELINE_RESULT)
    assert isinstance(pipeline_result, PipelineResult)
    assert pipeline_result is result
    assert pipeline_result.status == ExecutionStatus.COMPLETED
