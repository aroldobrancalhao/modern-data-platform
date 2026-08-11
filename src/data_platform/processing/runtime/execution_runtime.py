"""
Modern Data Platform
Processing Framework

Execution runtime.

Responsible for synchronizing execution lifecycle
information with the ProcessingContext.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from contextvars import ContextVar
from datetime import UTC, datetime

from data_platform.processing.core.context_keys.execution_keys import (
    ExecutionKeys,
)
from data_platform.processing.core.context_keys.processing_keys import (
    ProcessingKeys,
)
from data_platform.processing.core.execution_status import (
    ExecutionStatus,
)
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.core.stage_result import StageResult

# Stage-scoped execution state -- which stage/attempt is currently
# running, its last result, its last exception, its max_attempts --
# lives in these ContextVars instead of ProcessingContext. This is
# specifically so ParallelExecutor's concurrent stages, each running
# as its own asyncio.Task (gather gives every Task an independent copy
# of the current contextvars.Context at creation time), never collide
# on a single shared slot the way a plain ProcessingContext key would.
# Confirmed live this was a real bug, not a hypothetical one: the
# previous single-slot design made a Hook/Policy reading mid-flight
# during concurrent execution liable to observe the wrong stage's
# data (see "Item 2 (parallelize flushes)" and the ParallelExecutor
# entries in docs/architecture/roadmap-next-steps.md for the
# investigation that found this).
#
# Pipeline-level state (STATUS, START_TIME/END_TIME/DURATION,
# CANCELLED, PIPELINE_RESULT) stays on ProcessingContext below --
# there is only ever one of those per execute() call, concurrent
# stages or not, so there is nothing to isolate.
_current_stage: ContextVar[str | None] = ContextVar(
    "current_stage", default=None
)

_current_attempt: ContextVar[int | None] = ContextVar(
    "current_attempt", default=None
)

_max_attempts: ContextVar[int | None] = ContextVar(
    "max_attempts", default=None
)

_stage_result: ContextVar[StageResult | None] = ContextVar(
    "stage_result", default=None
)

_stage_exception: ContextVar[Exception | None] = ContextVar(
    "stage_exception", default=None
)


def current_stage_id() -> str | None:
    """The id of the stage currently running in this context, if any."""
    return _current_stage.get()


def current_attempt() -> int:
    """The current stage's attempt number (1 if none is in flight)."""
    return _current_attempt.get() or 1


def current_max_attempts() -> int:
    """The current stage's configured max_attempts (1 if none is in flight)."""
    return _max_attempts.get() or 1


def current_stage_result() -> StageResult | None:
    """The current stage's last recorded StageResult, if any."""
    return _stage_result.get()


def current_stage_exception() -> Exception | None:
    """The current stage's last recorded exception, if any."""
    return _stage_exception.get()


class ExecutionRuntime:
    """
    Synchronizes execution state with the ProcessingContext (pipeline-
    level state) and with the module-level ContextVars above (stage-
    level state -- see the comment there for why the split exists).

    This class is the single writer of execution state.

    Executors, policies and hooks should never manipulate
    ProcessingContext (or the stage-level ContextVars) directly for
    runtime state -- policies read the stage-level state via the
    module-level current_*() functions above (see PolicyContext).
    """

    def __init__(
        self,
        context: ProcessingContext,
    ) -> None:
        self._context = context

    # ------------------------------------------------------------------
    # Pipeline lifecycle
    # ------------------------------------------------------------------

    def execution_started(self) -> None:
        started_at = datetime.now(UTC)

        self._context.set(
            ExecutionKeys.STATUS,
            ExecutionStatus.RUNNING,
        )

        self._context.set(
            ExecutionKeys.START_TIME,
            started_at,
        )

        self._context.remove(
            ExecutionKeys.END_TIME,
        )

        self._context.remove(
            ExecutionKeys.DURATION,
        )

        _stage_exception.set(None)

        self._context.remove(
            ProcessingKeys.PIPELINE_RESULT,
        )

        _stage_result.set(None)

        self._context.set(
            ProcessingKeys.CANCELLED,
            False,
        )

    def execution_completed(self) -> None:
        finished_at = datetime.now(UTC)

        self._context.set(
            ExecutionKeys.STATUS,
            ExecutionStatus.COMPLETED,
        )

        self._context.set(
            ExecutionKeys.END_TIME,
            finished_at,
        )

        started_at = self._context.get(
            ExecutionKeys.START_TIME,
        )

        if started_at is not None:
            self._context.set(
                ExecutionKeys.DURATION,
                finished_at - started_at,
            )

        _stage_exception.set(None)

    def execution_failed(
        self,
        exception: Exception | None = None,
    ) -> None:
        finished_at = datetime.now(UTC)

        self._context.set(
            ExecutionKeys.STATUS,
            ExecutionStatus.FAILED,
        )

        self._context.set(
            ExecutionKeys.END_TIME,
            finished_at,
        )

        started_at = self._context.get(
            ExecutionKeys.START_TIME,
        )

        if started_at is not None:
            self._context.set(
                ExecutionKeys.DURATION,
                finished_at - started_at,
            )

        if exception is not None:
            _stage_exception.set(exception)

    def execution_cancelled(self) -> None:
        self._context.set(
            ProcessingKeys.CANCELLED,
            True,
        )

    # ------------------------------------------------------------------
    # Stage lifecycle
    # ------------------------------------------------------------------

    def stage_started(
        self,
        stage_id: str,
    ) -> None:
        _current_stage.set(stage_id)

        _current_attempt.set(1)

        _stage_result.set(None)

        _stage_exception.set(None)

    def stage_finished(self) -> None:
        _current_stage.set(None)

        _current_attempt.set(None)

    def retry_started(
        self,
        attempt: int,
    ) -> None:
        _current_attempt.set(attempt)

        _stage_result.set(None)

        _stage_exception.set(None)

    def max_attempts(
        self,
        attempts: int,
    ) -> None:
        _max_attempts.set(attempts)

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def stage_result(
        self,
        result: StageResult,
    ) -> None:
        _stage_result.set(result)

    def pipeline_result(
        self,
        result: object,
    ) -> None:
        self._context.set(
            ProcessingKeys.PIPELINE_RESULT,
            result,
        )

    # ------------------------------------------------------------------
    # Exception
    # ------------------------------------------------------------------

    def stage_failed(
        self,
        exception: Exception,
    ) -> None:
        _stage_exception.set(exception)
