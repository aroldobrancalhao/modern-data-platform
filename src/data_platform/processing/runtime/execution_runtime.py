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


class ExecutionRuntime:
    """
    Synchronizes execution state with the ProcessingContext.

    This class is the single writer of execution state.

    Executors, policies and hooks should never manipulate
    ProcessingContext directly for runtime state.
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

        self._context.remove(
            ProcessingKeys.EXCEPTION,
        )

        self._context.remove(
            ProcessingKeys.PIPELINE_RESULT,
        )

        self._context.remove(
            ProcessingKeys.STAGE_RESULT,
        )

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

        self._context.remove(
            ProcessingKeys.EXCEPTION,
        )

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
            self._context.set(
                ProcessingKeys.EXCEPTION,
                exception,
            )

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
        self._context.set(
            ProcessingKeys.CURRENT_STAGE,
            stage_id,
        )

        self._context.set(
            ProcessingKeys.CURRENT_ATTEMPT,
            1,
        )

        self._context.remove(
            ProcessingKeys.STAGE_RESULT,
        )

        self._context.remove(
            ProcessingKeys.EXCEPTION,
        )

    def stage_finished(self) -> None:
        self._context.remove(
            ProcessingKeys.CURRENT_STAGE,
        )

        self._context.remove(
            ProcessingKeys.CURRENT_ATTEMPT,
        )

    def retry_started(
        self,
        attempt: int,
    ) -> None:
        self._context.set(
            ProcessingKeys.CURRENT_ATTEMPT,
            attempt,
        )

        self._context.remove(
            ProcessingKeys.STAGE_RESULT,
        )

        self._context.remove(
            ProcessingKeys.EXCEPTION,
        )

    def max_attempts(
        self,
        attempts: int,
    ) -> None:
        self._context.set(
            ProcessingKeys.MAX_ATTEMPTS,
            attempts,
        )

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def stage_result(
        self,
        result: object,
    ) -> None:
        self._context.set(
            ProcessingKeys.STAGE_RESULT,
            result,
        )

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
        self._context.set(
            ProcessingKeys.EXCEPTION,
            exception,
        )