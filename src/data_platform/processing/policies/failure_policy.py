"""
Modern Data Platform
Processing Framework

Failure handling policy.
"""

from __future__ import annotations

from dataclasses import dataclass

from data_platform.processing.policies.policy import (
    Policy,
)
from data_platform.processing.policies.policy_context import (
    PolicyContext,
)
from data_platform.processing.policies.policy_result import (
    PolicyResult,
)


@dataclass(frozen=True, slots=True)
class FailurePolicy(Policy):
    """
    Controls pipeline behavior after failures.

    Parameters
    ----------
    fail_fast:
        Stops the pipeline immediately after the first failure.
    """

    fail_fast: bool = True

    async def evaluate(
        self,
        context: PolicyContext,
    ) -> PolicyResult:
        """
        Evaluates the failure policy.
        """

        exception = context.processing_context.get(
            "exception",
        )

        if exception is None:
            return PolicyResult()

        if self.fail_fast:
            return PolicyResult(
                continue_execution=False,
                cancel_pipeline=True,
                reason="Pipeline interrupted due to failure.",
            )

        return PolicyResult(
            continue_execution=True,
            cancel_pipeline=False,
            reason="Failure ignored by policy.",
        )