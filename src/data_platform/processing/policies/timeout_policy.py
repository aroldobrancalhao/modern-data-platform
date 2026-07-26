"""
Modern Data Platform
Processing Framework

Execution timeout policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime

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
class TimeoutPolicy(Policy):
    """
    Execution timeout policy.

    Parameters
    ----------
    timeout:
        Maximum execution time in seconds.
    """

    timeout: float

    async def evaluate(
        self,
        context: PolicyContext,
    ) -> PolicyResult:

        started_at = (
            context.processing_context.metadata.started_at
        )

        if started_at is None:
            return PolicyResult()

        elapsed = (
            datetime.now(UTC) - started_at
        ).total_seconds()

        if elapsed <= self.timeout:
            return PolicyResult()

        return PolicyResult(
            continue_execution=False,
            cancel_pipeline=True,
            reason="Execution timeout exceeded.",
        )