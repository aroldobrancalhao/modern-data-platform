"""
Modern Data Platform
Processing Framework

Retry policy.
"""

from __future__ import annotations

from dataclasses import dataclass

from data_platform.processing.events.hook_context import (
    HookContext,
)

from .policy import Policy
from .policy_result import PolicyResult


@dataclass(frozen=True, slots=True)
class RetryPolicy(Policy):
    """
    Retry policy.

    Parameters
    ----------
    max_attempts:
        Maximum retry attempts.
    """

    max_attempts: int = 3

    async def evaluate(
        self,
        context: HookContext,
    ) -> PolicyResult:

        if context.exception is None:
            return PolicyResult()

        return PolicyResult(
            retry=True,
            continue_execution=True,
            reason="Retry requested.",
        )