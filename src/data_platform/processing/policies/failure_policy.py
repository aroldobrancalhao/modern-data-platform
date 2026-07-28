"""
Modern Data Platform
Processing Framework

Failure handling policy.

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
class FailurePolicy(Policy):
    """
    Controls pipeline behavior after non-recoverable business failures.

    Retry decisions are handled exclusively by RetryPolicy.
    """

    fail_fast: bool = True

    async def evaluate(
        self,
        context: PolicyContext,
    ) -> PolicyResult:
        """
        Evaluates the failure policy.
        """

        #
        # Ignore every event except stage failures.
        #
        if context.event is not PolicyEvent.STAGE_FAILED:
            return PolicyResult()

        #
        # Technical exceptions are handled exclusively
        # by RetryPolicy.
        #
        if context.exception is not None:
            return PolicyResult()

        #
        # Ignore successful stage executions.
        #
        if not context.failed:
            return PolicyResult()

        #
        # Business failure.
        #
        if self.fail_fast:
            return PolicyResult(
                continue_execution=False,
                retry=False,
                cancel_pipeline=True,
                reason="Pipeline interrupted due to stage failure.",
            )

        return PolicyResult(
            continue_execution=True,
            retry=False,
            cancel_pipeline=False,
            reason="Stage failure ignored by policy.",
        )