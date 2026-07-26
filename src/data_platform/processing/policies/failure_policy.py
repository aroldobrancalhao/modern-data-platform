"""
Modern Data Platform
Processing Framework

Failure handling policy.
"""

from __future__ import annotations

from dataclasses import dataclass

from data_platform.processing.events.hook_context import (
    HookContext,
)

from .policy import Policy
from .policy_result import PolicyResult


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
        context: HookContext,
    ) -> PolicyResult:

        if context.exception is None:
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