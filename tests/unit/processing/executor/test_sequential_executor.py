"""
Modern Data Platform
Processing Framework

Unit tests for SequentialExecutor.

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
from data_platform.processing.events.hook_context import HookContext
from data_platform.processing.events.hook_type import HookType
from data_platform.processing.policies.failure_policy import FailurePolicy
from data_platform.processing.policies.policy_manager import PolicyManager
from data_platform.processing.executor.sequential_executor import (
    SequentialExecutor,
)
from data_platform.processing.runtime.execution_runtime import (
    ExecutionKeys,
)
from data_platform.processing.core.context_keys.processing_keys import (
    ProcessingKeys,
)
from data_platform.processing.hooks.hook import Hook

import pytest

pytestmark = pytest.mark.anyio


class SuccessfulStage(Stage):
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


class FailedStage(Stage):
    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:
        return StageResult(
            status=ExecutionStatus.FAILED,
            metadata=context.metadata,
            stage_id=self.id,
            stage_name=self.name,
            error_type="ValidationError",
            error_message="Stage failed.",
        )


class ExceptionStage(Stage):
    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:
        raise RuntimeError("boom")


class RecordingHook(Hook):
    def __init__(self) -> None:
        self.events: list[HookType] = []

    async def execute(
        self,
        context: HookContext,
    ) -> None:
        self.events.append(context.hook_type)


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-1",
        metadata=ExecutionMetadata(
            execution_id="execution-1",
        ),
    )


def create_pipeline(*stages: Stage) -> Pipeline:
    return Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=tuple(stages),
    )


async def test_execute_single_stage_success() -> None:
    executor = SequentialExecutor()

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
    )

    result = await executor.execute(
        pipeline,
        create_context(),
    )

    assert result.status == ExecutionStatus.COMPLETED
    assert result.total_stages == 1
    assert result.successful_stages == 1
    assert result.failed_stages == 0
    assert result.has_failures is False


async def test_execute_multiple_stages_success() -> None:
    executor = SequentialExecutor()

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
        SuccessfulStage(
            id="transform",
            name="Transform",
        ),
        SuccessfulStage(
            id="load",
            name="Load",
        ),
    )

    result = await executor.execute(
        pipeline,
        create_context(),
    )

    assert result.status == ExecutionStatus.COMPLETED
    assert result.total_stages == 3
    assert result.successful_stages == 3
    assert result.failed_stages == 0
    assert result.last_result is not None
    assert result.last_result.stage_id == "load"

async def test_execute_stops_after_first_failure() -> None:
    executor = SequentialExecutor()

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
        FailedStage(
            id="transform",
            name="Transform",
        ),
        SuccessfulStage(
            id="load",
            name="Load",
        ),
    )

    result = await executor.execute(
        pipeline,
        create_context(),
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.total_stages == 2
    assert result.successful_stages == 1
    assert result.failed_stages == 1
    assert result.has_failures is True

    assert result.last_result is not None
    assert result.last_result.stage_id == "transform"


async def test_execute_propagates_stage_error() -> None:
    executor = SequentialExecutor()

    pipeline = create_pipeline(
        FailedStage(
            id="extract",
            name="Extract",
        ),
    )

    result = await executor.execute(
        pipeline,
        create_context(),
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.error_type == "ValidationError"
    assert result.error_message == "Stage failed."


async def test_execute_preserves_stage_results_order() -> None:
    executor = SequentialExecutor()

    pipeline = create_pipeline(
        SuccessfulStage(
            id="one",
            name="One",
        ),
        SuccessfulStage(
            id="two",
            name="Two",
        ),
        SuccessfulStage(
            id="three",
            name="Three",
        ),
    )

    result = await executor.execute(
        pipeline,
        create_context(),
    )

    assert [stage.stage_id for stage in result.stage_results] == [
        "one",
        "two",
        "three",
    ]


async def test_execute_preserves_metadata() -> None:
    context = create_context()

    executor = SequentialExecutor()

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
    )

    result = await executor.execute(
        pipeline,
        context,
    )

    assert result.metadata is context.metadata


async def test_execute_last_result_returns_failed_stage() -> None:
    executor = SequentialExecutor()

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
        FailedStage(
            id="transform",
            name="Transform",
        ),
    )

    result = await executor.execute(
        pipeline,
        create_context(),
    )

    assert result.last_result is not None
    assert result.last_result.stage_id == "transform"
    assert result.last_result.failed is True


async def test_hooks_success_execution_order() -> None:
    executor = SequentialExecutor()

    hook = RecordingHook()

    for hook_type in HookType:
        executor.register_hook(hook_type, hook)

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
        SuccessfulStage(
            id="load",
            name="Load",
        ),
    )

    result = await executor.execute(
        pipeline,
        create_context(),
    )

    assert result.status == ExecutionStatus.COMPLETED

    assert hook.events == [
        HookType.BEFORE_PIPELINE,
        HookType.BEFORE_STAGE,
        HookType.AFTER_STAGE,
        HookType.BEFORE_STAGE,
        HookType.AFTER_STAGE,
        HookType.AFTER_PIPELINE,
    ]


async def test_hooks_stage_failure() -> None:
    executor = SequentialExecutor()

    hook = RecordingHook()

    for hook_type in HookType:
        executor.register_hook(hook_type, hook)

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
        FailedStage(
            id="transform",
            name="Transform",
        ),
    )

    result = await executor.execute(
        pipeline,
        create_context(),
    )

    assert result.status == ExecutionStatus.FAILED

    assert hook.events == [
        HookType.BEFORE_PIPELINE,
        HookType.BEFORE_STAGE,
        HookType.AFTER_STAGE,
        HookType.BEFORE_STAGE,
        HookType.STAGE_FAILED,
        HookType.PIPELINE_FAILED,
    ]


async def test_hooks_exception() -> None:
    """
    max_attempts=1 pins this stage to a single attempt: the default
    PolicyManager now includes RetryPolicy, which would otherwise
    retry this raised exception and emit STAGE_FAILED once per
    attempt -- this test is about hook dispatch shape, not retries.
    """

    executor = SequentialExecutor()

    hook = RecordingHook()

    for hook_type in HookType:
        executor.register_hook(hook_type, hook)

    pipeline = create_pipeline(
        ExceptionStage(
            id="extract",
            name="Extract",
            max_attempts=1,
        ),
    )

    result = await executor.execute(
        pipeline,
        create_context(),
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.error_type == "RuntimeError"
    assert result.error_message == "boom"

    assert hook.events == [
        HookType.BEFORE_PIPELINE,
        HookType.BEFORE_STAGE,
        HookType.STAGE_FAILED,
        HookType.PIPELINE_FAILED,
    ]

class ContextHook(Hook):
    def __init__(self) -> None:
        self.contexts: list[HookContext] = []

    async def execute(
        self,
        context: HookContext,
    ) -> None:
        self.contexts.append(context)


async def test_hook_receives_processing_context() -> None:
    executor = SequentialExecutor()

    hook = ContextHook()

    executor.register_hook(
        HookType.BEFORE_STAGE,
        hook,
    )

    context = create_context()

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
    )

    await executor.execute(
        pipeline,
        context,
    )

    assert len(hook.contexts) == 1

    hook_context = hook.contexts[0]

    assert hook_context.processing_context is context
    assert hook_context.pipeline is pipeline
    assert hook_context.stage is pipeline.stages[0]
    assert hook_context.exception is None

async def test_hook_receives_exception() -> None:
    executor = SequentialExecutor()

    hook = ContextHook()

    executor.register_hook(
        HookType.STAGE_FAILED,
        hook,
    )

    pipeline = create_pipeline(
        ExceptionStage(
            id="extract",
            name="Extract",
            max_attempts=1,
        ),
    )

    await executor.execute(
        pipeline,
        create_context(),
    )

    assert len(hook.contexts) == 1

    exception = hook.contexts[0].exception

    assert exception is not None
    assert isinstance(
        exception,
        RuntimeError,
    )
    assert str(exception) == "boom"

async def test_multiple_hooks_receive_same_event() -> None:
    executor = SequentialExecutor()

    hook1 = RecordingHook()
    hook2 = RecordingHook()

    executor.register_hook(
        HookType.AFTER_STAGE,
        hook1,
    )
    executor.register_hook(
        HookType.AFTER_STAGE,
        hook2,
    )

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
    )

    await executor.execute(
        pipeline,
        create_context(),
    )

    assert hook1.events == [
        HookType.AFTER_STAGE,
    ]

    assert hook2.events == [
        HookType.AFTER_STAGE,
    ]

async def test_unregister_hook() -> None:
    executor = SequentialExecutor()

    hook = RecordingHook()

    executor.register_hook(
        HookType.AFTER_STAGE,
        hook,
    )

    executor.unregister_hook(
        HookType.AFTER_STAGE,
        hook,
    )

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
    )

    await executor.execute(
        pipeline,
        create_context(),
    )

    assert hook.events == []

async def test_clear_hooks() -> None:
    executor = SequentialExecutor()

    hook = RecordingHook()

    for hook_type in HookType:
        executor.register_hook(
            hook_type,
            hook,
        )

    executor.clear_hooks()

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
    )

    await executor.execute(
        pipeline,
        create_context(),
    )

    assert hook.events == []

class OrderedHook(Hook):
    def __init__(
        self,
        name: str,
        events: list[str],
    ) -> None:
        self._name = name
        self._events = events

    async def execute(
        self,
        context: HookContext,
    ) -> None:
        self._events.append(self._name)


async def test_hooks_execute_in_registration_order() -> None:
    executor = SequentialExecutor()

    execution_order: list[str] = []

    executor.register_hook(
        HookType.AFTER_STAGE,
        OrderedHook(
            "A",
            execution_order,
        ),
    )

    executor.register_hook(
        HookType.AFTER_STAGE,
        OrderedHook(
            "B",
            execution_order,
        ),
    )

    executor.register_hook(
        HookType.AFTER_STAGE,
        OrderedHook(
            "C",
            execution_order,
        ),
    )

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
    )

    await executor.execute(
        pipeline,
        create_context(),
    )

    assert execution_order == [
        "A",
        "B",
        "C",
    ]


async def test_execution_runtime_marks_execution_completed() -> None:
    executor = SequentialExecutor()

    context = create_context()

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
    )

    result = await executor.execute(
        pipeline,
        context,
    )

    assert result.status == ExecutionStatus.COMPLETED

    assert (
        context.get(ExecutionKeys.STATUS)
        == ExecutionStatus.COMPLETED
    )

    assert context.contains(
        ExecutionKeys.START_TIME,
    )

    assert context.contains(
        ExecutionKeys.END_TIME,
    )

    assert context.contains(
        ExecutionKeys.DURATION,
    )


async def test_execution_runtime_marks_execution_failed() -> None:
    executor = SequentialExecutor()

    context = create_context()

    pipeline = create_pipeline(
        ExceptionStage(
            id="extract",
            name="Extract",
        ),
    )

    result = await executor.execute(
        pipeline,
        context,
    )

    assert result.status == ExecutionStatus.FAILED

    assert (
        context.get(ExecutionKeys.STATUS)
        == ExecutionStatus.FAILED
    )

    assert context.contains(
        ExecutionKeys.END_TIME,
    )

    assert context.contains(
        ExecutionKeys.DURATION,
    )

    exception = context.get(
        ProcessingKeys.EXCEPTION,
    )

    assert exception is not None


async def test_current_stage_is_cleared_after_execution() -> None:
    executor = SequentialExecutor()

    context = create_context()

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
    )

    await executor.execute(
        pipeline,
        context,
    )

    assert not context.contains(
        ProcessingKeys.CURRENT_STAGE,
    )


# ============================================================================
# Runtime integration
# ============================================================================

async def test_runtime_stores_stage_result() -> None:
    executor = SequentialExecutor()

    context = create_context()

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
    )

    result = await executor.execute(
        pipeline,
        context,
    )

    assert (
        context.get(
            ProcessingKeys.STAGE_RESULT,
        )
        is result.last_result
    )


async def test_runtime_stores_max_attempts() -> None:
    executor = SequentialExecutor()

    context = create_context()

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
            max_attempts=7,
        ),
    )

    await executor.execute(
        pipeline,
        context,
    )

    assert (
        context.get(
            ProcessingKeys.MAX_ATTEMPTS,
        )
        == 7
    )


async def test_failure_policy_fail_fast_cancels_pipeline() -> None:
    executor = SequentialExecutor(
        policy_manager=PolicyManager(
            (
                FailurePolicy(
                    fail_fast=True,
                ),
            ),
        ),
    )

    pipeline = create_pipeline(
        FailedStage(
            id="extract",
            name="Extract",
        ),
        SuccessfulStage(
            id="load",
            name="Load",
        ),
    )

    result = await executor.execute(
        pipeline,
        create_context(),
    )

    assert result.status == ExecutionStatus.FAILED

    assert result.total_stages == 1

    assert result.failed_stages == 1

    assert result.last_result is not None

    assert result.last_result.stage_id == "extract"


async def test_failure_policy_continue_execution() -> None:
    executor = SequentialExecutor(
        policy_manager=PolicyManager(
            (
                FailurePolicy(
                    fail_fast=False,
                ),
            ),
        ),
    )

    pipeline = create_pipeline(
        FailedStage(
            id="extract",
            name="Extract",
        ),
        SuccessfulStage(
            id="load",
            name="Load",
        ),
    )

    result = await executor.execute(
        pipeline,
        create_context(),
    )

    assert result.status == ExecutionStatus.FAILED

    assert result.total_stages == 2
    assert result.successful_stages == 1
    assert result.failed_stages == 1

    assert result.last_result is not None
    assert result.last_result.stage_id == "load"