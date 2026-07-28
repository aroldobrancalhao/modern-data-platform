"""
Modern Data Platform
Processing Framework

Unit tests for ExecutionRuntime.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from datetime import timedelta

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
)


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

    context.set(
        ProcessingKeys.EXCEPTION,
        RuntimeError("old"),
    )

    runtime.execution_started()

    assert not context.contains(
        ProcessingKeys.EXCEPTION,
    )


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

    assert (
        context.get(ProcessingKeys.EXCEPTION)
        is exception
    )


def test_stage_started_sets_current_stage() -> None:
    """
    stage_started() should store the current stage id.
    """

    runtime, context = create_runtime()

    runtime.stage_started("customers")

    assert (
        context.get(
            ProcessingKeys.CURRENT_STAGE,
        )
        == "customers"
    )


def test_stage_finished_clears_current_stage() -> None:
    """
    stage_finished() should clear CURRENT_STAGE.
    """

    runtime, context = create_runtime()

    runtime.stage_started("customers")
    runtime.stage_finished()

    assert not context.contains(
        ProcessingKeys.CURRENT_STAGE,
    )


def test_execution_started_clears_previous_stage_result() -> None:

    runtime, context = create_runtime()

    context.set(
        ProcessingKeys.STAGE_RESULT,
        object(),
    )

    runtime.execution_started()

    assert not context.contains(
        ProcessingKeys.STAGE_RESULT,
    )


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

    assert (
        context.get(
            ProcessingKeys.CURRENT_ATTEMPT,
        )
        == 2
    )


def test_retry_started_clears_previous_exception() -> None:

    runtime, context = create_runtime()

    context.set(
        ProcessingKeys.EXCEPTION,
        RuntimeError(),
    )

    runtime.retry_started(2)

    assert not context.contains(
        ProcessingKeys.EXCEPTION,
    )


def test_retry_started_clears_stage_result() -> None:

    runtime, context = create_runtime()

    context.set(
        ProcessingKeys.STAGE_RESULT,
        object(),
    )

    runtime.retry_started(2)

    assert not context.contains(
        ProcessingKeys.STAGE_RESULT,
    )


def test_max_attempts_sets_value() -> None:

    runtime, context = create_runtime()

    runtime.max_attempts(5)

    assert (
        context.get(
            ProcessingKeys.MAX_ATTEMPTS,
        )
        == 5
    )


def test_stage_result_is_stored() -> None:

    runtime, context = create_runtime()

    result = object()

    runtime.stage_result(result)

    assert (
        context.get(
            ProcessingKeys.STAGE_RESULT,
        )
        is result
    )


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

    assert (
        context.get(
            ProcessingKeys.EXCEPTION,
        )
        is exception
    )