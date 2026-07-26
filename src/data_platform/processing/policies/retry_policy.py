"""
Modern Data Platform
Processing Framework

Retry execution policy.
"""

from __future__ import annotations

from data_platform.processing.policies.policy import Policy
from data_platform.processing.policies.policy_context import (
    PolicyContext,
)
from data_platform.processing.policies.policy_result import (
    PolicyResult,
)


class RetryPolicy(Policy):
    """
    Placeholder retry policy.

    Retry behavior will be implemented in a future sprint.
    """

    async def evaluate(
        self,
        context: PolicyContext,
    ) -> PolicyResult:
        return PolicyResult()