"""
Modern Data Platform
Processing Framework

Retry execution policy.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass

from data_platform.processing.policies.policy import Policy
from data_platform.processing.policies.policy_context import PolicyContext
from data_platform.processing.policies.policy_event import PolicyEvent
from data_platform.processing.policies.policy_result import PolicyResult


@dataclass(frozen=True, slots=True)
class RetryPolicy(Policy):
    """
    Determines whether a failed execution should be retried.

    This policy is responsible only for technical failures
    represented by exceptions.
    """

    async def evaluate(
        self,
        context: PolicyContext,
    ) -> PolicyResult:
        """
        Evaluates whether the current execution should be retried.
        """

        if context.event is not PolicyEvent.STAGE_FAILED:
            return PolicyResult()

        if context.exception is None:
            return PolicyResult()

        if context.current_attempt < context.max_attempts:
            return PolicyResult(
                continue_execution=True,
                retry=True,
                cancel_pipeline=False,
                reason="Retry allowed.",
            )

        return PolicyResult(
            continue_execution=True,
            retry=False,
            cancel_pipeline=False,
            reason="Maximum retry attempts reached.",
        )