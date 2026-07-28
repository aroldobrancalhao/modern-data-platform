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


@dataclass(slots=True)
class PolicyContext:
    """
    Read-only view exposed to execution policies.

    The execution state remains owned by ProcessingContext.
    This class provides a typed projection of the information
    required by policies.
    """

    processing_context: ProcessingContext

    pipeline: Pipeline | None = None

    stage: Stage | None = None

    event: PolicyEvent = PolicyEvent.BEFORE_PIPELINE

    @property
    def exception(self) -> Exception | None:
        return self.processing_context.get(
            ProcessingKeys.EXCEPTION,
        )

    @property
    def stage_result(self) -> StageResult | None:
        return self.processing_context.get(
            ProcessingKeys.STAGE_RESULT,
        )

    @property
    def current_attempt(self) -> int:
        return self.processing_context.get(
            ProcessingKeys.CURRENT_ATTEMPT,
            1,
        )

    @property
    def max_attempts(self) -> int:
        return self.processing_context.get(
            ProcessingKeys.MAX_ATTEMPTS,
            1,
        )

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