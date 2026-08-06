from __future__ import annotations

from dataclasses import dataclass

from data_platform.processing.core.context_keys import (
    ProcessingKeys,
)
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult
from data_platform.processing.policies.policy_event import PolicyEvent
from data_platform.processing.runtime import execution_runtime


@dataclass(slots=True)
class PolicyContext:
    """
    Read-only view exposed to execution policies.

    ``cancelled`` (pipeline-level -- there is only ever one per
    execute() call) still reads from ProcessingContext. The rest --
    exception/stage_result/current_attempt/max_attempts -- are
    stage-level: they read from execution_runtime's ContextVars, not
    ProcessingContext, so a policy evaluated for one stage's failure
    can't observe a concurrently-running sibling's data (see
    execution_runtime.py's module docstring comment).
    """

    processing_context: ProcessingContext

    pipeline: Pipeline | None = None

    stage: Stage | None = None

    event: PolicyEvent = PolicyEvent.BEFORE_PIPELINE

    @property
    def exception(self) -> Exception | None:
        return execution_runtime.current_stage_exception()

    @property
    def stage_result(self) -> StageResult | None:
        return execution_runtime.current_stage_result()

    @property
    def current_attempt(self) -> int:
        return execution_runtime.current_attempt()

    @property
    def max_attempts(self) -> int:
        return execution_runtime.current_max_attempts()

    @property
    def cancelled(self) -> bool:
        return self.processing_context.get(
            ProcessingKeys.CANCELLED,
            False,
        )

    @property
    def failed(self) -> bool:
        """
        Returns True when the current stage produced a failed result.
        """

        result = self.stage_result

        return (
            result is not None
            and result.failed
        )