"""
Modern Data Platform
Processing Framework

Unit tests for ExecutionRuntime.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest

from data_platform.processing.core.context_keys.execution_keys import (
    ExecutionKeys,
)
from data_platform.processing.core.context_keys.processing_keys import (
    ProcessingKeys,
)
from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.execution_status import (
    ExecutionStatus,
)
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.runtime.execution_runtime import (
    ExecutionRuntime,
    current_attempt,
    current_max_attempts,
    current_stage_exception,
    current_stage_id,
    current_stage_result,
)

pytestmark = pytest.mark.anyio


def create_context() -> ProcessingContext:
    """
    Creates a ProcessingContext for testing.
    """

    return ProcessingContext(
        id="context-1",
        metadata=ExecutionMetadata(
            execution_id="execution-1",
        ),
    )


def create_runtime() -> tuple[ExecutionRuntime, ProcessingContext]:
    """
    Creates an ExecutionRuntime for testing.
    """

    context = create_context()

    return (
        ExecutionRuntime(context),
        context,
    )


def test_execution_started_sets_running_status() -> None:
    """
    execution_started() should mark the execution as RUNNING.
    """

    runtime, context = create_runtime()

    runtime.execution_started()

    assert context.get(ExecutionKeys.STATUS) == ExecutionStatus.RUNNING


def test_execution_started_sets_start_time() -> None:
    """
    execution_started() should populate START_TIME.
    """

    runtime, context = create_runtime()

    runtime.execution_started()

    assert context.contains(ExecutionKeys.START_TIME)


def test_execution_started_clears_end_time() -> None:
    """
    execution_started() should clear END_TIME.
    """

    runtime, context = create_runtime()

    context.set(ExecutionKeys.END_TIME, "finished")

    runtime.execution_started()

    assert not context.contains(ExecutionKeys.END_TIME)


def test_execution_started_clears_duration() -> None:
    """
    execution_started() should clear DURATION.
    """

    runtime, context = create_runtime()

    context.set(ExecutionKeys.DURATION, timedelta(seconds=10))

    runtime.execution_started()

    assert not context.contains(ExecutionKeys.DURATION)


def test_execution_started_clears_previous_exception() -> None:
    """
    execution_started() should remove stale exceptions.
    """

    runtime, context = create_runtime()

    runtime.stage_failed(
        RuntimeError("old"),
    )

    runtime.execution_started()

    assert current_stage_exception() is None


def test_execution_completed_sets_completed_status() -> None:
    """
    execution_completed() should mark the execution as COMPLETED.
    """

    runtime, context = create_runtime()

    runtime.execution_started()
    runtime.execution_completed()

    assert (
        context.get(ExecutionKeys.STATUS)
        == ExecutionStatus.COMPLETED
    )


def test_execution_completed_sets_end_time() -> None:
    """
    execution_completed() should populate END_TIME.
    """

    runtime, context = create_runtime()

    runtime.execution_started()
    runtime.execution_completed()

    assert context.contains(
        ExecutionKeys.END_TIME,
    )


def test_execution_completed_calculates_duration() -> None:
    """
    execution_completed() should calculate execution duration.
    """

    runtime, context = create_runtime()

    runtime.execution_started()
    runtime.execution_completed()

    duration = context.get(
        ExecutionKeys.DURATION,
    )

    assert duration is not None
    assert duration >= timedelta(0)


def test_execution_failed_sets_failed_status() -> None:
    """
    execution_failed() should mark the execution as FAILED.
    """

    runtime, context = create_runtime()

    runtime.execution_started()
    runtime.execution_failed()

    assert (
        context.get(ExecutionKeys.STATUS)
        == ExecutionStatus.FAILED
    )


def test_execution_failed_sets_end_time() -> None:
    """
    execution_failed() should populate END_TIME.
    """

    runtime, context = create_runtime()

    runtime.execution_started()
    runtime.execution_failed()

    assert context.contains(
        ExecutionKeys.END_TIME,
    )


def test_execution_failed_calculates_duration() -> None:
    """
    execution_failed() should calculate execution duration.
    """

    runtime, context = create_runtime()

    runtime.execution_started()
    runtime.execution_failed()

    duration = context.get(
        ExecutionKeys.DURATION,
    )

    assert duration is not None
    assert duration >= timedelta(0)


def test_execution_failed_stores_exception() -> None:
    """
    execution_failed() should store the raised exception.
    """

    runtime, context = create_runtime()

    exception = RuntimeError("boom")

    runtime.execution_started()
    runtime.execution_failed(exception)

    assert current_stage_exception() is exception


def test_stage_started_sets_current_stage() -> None:
    """
    stage_started() should store the current stage id.
    """

    runtime, context = create_runtime()

    runtime.stage_started("customers")

    assert current_stage_id() == "customers"


def test_stage_finished_clears_current_stage() -> None:
    """
    stage_finished() should clear CURRENT_STAGE.
    """

    runtime, context = create_runtime()

    runtime.stage_started("customers")
    runtime.stage_finished()

    assert current_stage_id() is None


def test_execution_started_clears_previous_stage_result() -> None:

    runtime, context = create_runtime()

    runtime.stage_result(
        object(),
    )

    runtime.execution_started()

    assert current_stage_result() is None


def test_execution_started_clears_previous_pipeline_result() -> None:

    runtime, context = create_runtime()

    context.set(
        ProcessingKeys.PIPELINE_RESULT,
        object(),
    )

    runtime.execution_started()

    assert not context.contains(
        ProcessingKeys.PIPELINE_RESULT,
    )


def test_execution_started_resets_cancelled_flag() -> None:

    runtime, context = create_runtime()

    context.set(
        ProcessingKeys.CANCELLED,
        True,
    )

    runtime.execution_started()

    assert (
        context.get(
            ProcessingKeys.CANCELLED,
        )
        is False
    )


def test_execution_cancelled_sets_cancelled_flag() -> None:

    runtime, context = create_runtime()

    runtime.execution_cancelled()

    assert (
        context.get(
            ProcessingKeys.CANCELLED,
        )
        is True
    )


def test_retry_started_updates_attempt() -> None:

    runtime, context = create_runtime()

    runtime.retry_started(2)

    assert current_attempt() == 2


def test_retry_started_clears_previous_exception() -> None:

    runtime, context = create_runtime()

    runtime.stage_failed(
        RuntimeError(),
    )

    runtime.retry_started(2)

    assert current_stage_exception() is None


def test_retry_started_clears_stage_result() -> None:

    runtime, context = create_runtime()

    runtime.stage_result(
        object(),
    )

    runtime.retry_started(2)

    assert current_stage_result() is None


def test_max_attempts_sets_value() -> None:

    runtime, context = create_runtime()

    runtime.max_attempts(5)

    assert current_max_attempts() == 5


def test_stage_result_is_stored() -> None:

    runtime, context = create_runtime()

    result = object()

    runtime.stage_result(result)

    assert current_stage_result() is result


def test_pipeline_result_is_stored() -> None:

    runtime, context = create_runtime()

    result = object()

    runtime.pipeline_result(result)

    assert (
        context.get(
            ProcessingKeys.PIPELINE_RESULT,
        )
        is result
    )


def test_stage_failed_stores_exception() -> None:

    runtime, context = create_runtime()

    exception = RuntimeError()

    runtime.stage_failed(exception)

    assert current_stage_exception() is exception


async def test_stage_scoped_state_is_isolated_across_concurrent_tasks() -> (
    None
):
    """
    Two "stages" running concurrently as separate asyncio.Tasks --
    exactly how ParallelExecutor runs a group -- must never see each
    other's stage-scoped runtime state, even though both calls go
    through the same ExecutionRuntime instance. This is the actual
    property the ContextVar-based redesign exists for (see
    execution_runtime.py's module docstring) -- proven here directly,
    independent of ParallelExecutor's own tests.
    """

    runtime, _ = create_runtime()

    both_started = asyncio.Event()

    arrived = 0

    async def run_stage(stage_id: str, result: object) -> tuple[str, object]:
        nonlocal arrived

        runtime.stage_started(stage_id)

        runtime.stage_result(result)

        arrived += 1

        if arrived == 2:
            both_started.set()

        # Deterministic rendezvous, not a sleep: both tasks must have
        # already set their own state above before either is allowed
        # to read it back below -- if the two Tasks were secretly
        # sharing state instead of isolated, this doesn't change the
        # outcome, but it does guarantee the race window is actually
        # exercised on every run instead of depending on scheduler
        # luck.
        await both_started.wait()

        return current_stage_id(), current_stage_result()

    outcome_a, outcome_b = await asyncio.gather(
        run_stage("stage-a", "result-a"),
        run_stage("stage-b", "result-b"),
    )

    assert outcome_a == ("stage-a", "result-a")
    assert outcome_b == ("stage-b", "result-b")