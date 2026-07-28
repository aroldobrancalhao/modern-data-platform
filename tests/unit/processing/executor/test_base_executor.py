"""
Modern Data Platform
Processing Framework

Unit tests for BaseExecutor.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.core.execution_metadata import ExecutionMetadata
from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.processing_context import ProcessingContext
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult
from data_platform.processing.executor.base_executor import BaseExecutor
from data_platform.processing.policies.policy import Policy
from data_platform.processing.policies.policy_context import PolicyContext
from data_platform.processing.policies.policy_event import PolicyEvent
from data_platform.processing.policies.policy_manager import PolicyManager
from data_platform.processing.policies.policy_result import PolicyResult

import pytest

pytestmark = pytest.mark.anyio

class DummyStage(Stage):
    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:
        return StageResult(
            status=ExecutionStatus.COMPLETED,
            metadata=context.metadata,
            stage_id=self.id,
            stage_name=self.name,
        )


class SuccessfulExecutor(BaseExecutor):
    async def _execute_pipeline(
        self,
        pipeline: Pipeline,
        context: ProcessingContext,
        stage_results: list[StageResult],
    ) -> ExecutionStatus:

        stage_results.append(
            StageResult(
                status=ExecutionStatus.COMPLETED,
                metadata=context.metadata,
                stage_id="stage-1",
                stage_name="Stage 1",
            )
        )

        return ExecutionStatus.COMPLETED


class FailedExecutor(BaseExecutor):
    async def _execute_pipeline(
        self,
        pipeline: Pipeline,
        context: ProcessingContext,
        stage_results: list[StageResult],
    ) -> ExecutionStatus:

        stage_results.append(
            StageResult(
                status=ExecutionStatus.FAILED,
                metadata=context.metadata,
                stage_id="stage-1",
                stage_name="Stage 1",
                error_type="ValidationError",
                error_message="Validation failed.",
            )
        )

        return ExecutionStatus.FAILED


class ExceptionExecutor(BaseExecutor):
    async def _execute_pipeline(
        self,
        pipeline: Pipeline,
        context: ProcessingContext,
        stage_results: list[StageResult],
    ) -> ExecutionStatus:

        raise RuntimeError("Unexpected failure")


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-1",
        metadata=ExecutionMetadata(
            execution_id="execution-1",
        ),
    )


def create_pipeline() -> Pipeline:
    return Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(
            DummyStage(
                id="stage-1",
                name="Stage 1",
            ),
        ),
    )


async def test_execute_returns_completed_pipeline_result() -> None:
    executor = SuccessfulExecutor()

    result = await executor.execute(
        create_pipeline(),
        create_context(),
    )

    assert result.status == ExecutionStatus.COMPLETED
    assert result.succeeded is True
    assert result.failed is False


async def test_execute_returns_failed_pipeline_result() -> None:
    executor = FailedExecutor()

    result = await executor.execute(
        create_pipeline(),
        create_context(),
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.failed is True
    assert result.succeeded is False


async def test_execute_preserves_stage_results() -> None:
    executor = SuccessfulExecutor()

    result = await executor.execute(
        create_pipeline(),
        create_context(),
    )

    assert len(result.stage_results) == 1
    assert result.total_stages == 1


async def test_execute_propagates_stage_error_information() -> None:
    executor = FailedExecutor()

    result = await executor.execute(
        create_pipeline(),
        create_context(),
    )

    assert result.error_type == "ValidationError"
    assert result.error_message == "Validation failed."


async def test_execute_handles_unexpected_exception() -> None:
    executor = ExceptionExecutor()

    result = await executor.execute(
        create_pipeline(),
        create_context(),
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.error_type == "RuntimeError"
    assert result.error_message == "Unexpected failure"


async def test_execute_preserves_metadata() -> None:
    context = create_context()

    executor = SuccessfulExecutor()

    result = await executor.execute(
        create_pipeline(),
        context,
    )

    assert result.metadata is context.metadata


async def test_execute_returns_empty_stage_results_when_exception_occurs() -> None:
    executor = ExceptionExecutor()

    result = await executor.execute(
        create_pipeline(),
        create_context(),
    )

    assert result.stage_results == ()

async def test_execute_stage_delegates_to_stage() -> None:
    executor = SuccessfulExecutor()

    stage = DummyStage(
        id="stage-1",
        name="Stage 1",
    )

    context = create_context()

    result = await executor._execute_stage(
        stage=stage,
        context=context,
    )

    assert result.stage_id == stage.id
    assert result.stage_name == stage.name
    assert result.status == ExecutionStatus.COMPLETED


async def test_execute_stage_preserves_metadata() -> None:
    executor = SuccessfulExecutor()

    context = create_context()

    stage = DummyStage(
        id="stage-1",
        name="Stage 1",
    )

    result = await executor._execute_stage(
        stage=stage,
        context=context,
    )

    assert result.metadata is context.metadata


async def test_execute_stage_propagates_stage_exception() -> None:

    class FailingStage(Stage):
        async def execute(
            self,
            context: ProcessingContext,
        ) -> StageResult:
            raise RuntimeError("boom")

    executor = SuccessfulExecutor()

    with pytest.raises(
        RuntimeError,
        match="boom",
    ):
        await executor._execute_stage(
            stage=FailingStage(
                id="stage-1",
                name="Stage 1",
            ),
            context=create_context(),
        )


class RetryPolicyStub(Policy):

    async def evaluate(
        self,
        context: PolicyContext,
    ) -> PolicyResult:

        return PolicyResult(
            retry=True,
        )


async def test_build_policy_context_should_preserve_values() -> None:

    executor = SuccessfulExecutor()

    pipeline = create_pipeline()
    context = create_context()
    stage = pipeline.stages[0]

    policy_context = executor._build_policy_context(
        processing_context=context,
        pipeline=pipeline,
        stage=stage,
        event=PolicyEvent.STAGE_FAILED,
    )

    assert policy_context.processing_context is context
    assert policy_context.pipeline is pipeline
    assert policy_context.stage is stage
    assert (
        policy_context.event
        == PolicyEvent.STAGE_FAILED
    )


async def test_evaluate_policies_should_delegate_to_policy_manager() -> None:

    executor = SuccessfulExecutor(
        policy_manager=PolicyManager(
            (
                RetryPolicyStub(),
            ),
        ),
    )

    pipeline = create_pipeline()
    context = create_context()

    result = await executor._evaluate_policies(
        processing_context=context,
        pipeline=pipeline,
        event=PolicyEvent.STAGE_FAILED,
        stage=pipeline.stages[0],
    )

    assert result.continue_execution is True
    assert result.retry is True
    assert result.cancel_pipeline is False