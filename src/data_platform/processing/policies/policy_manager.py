"""
Modern Data Platform
Processing Framework

Coordinates policy evaluation.
"""

from __future__ import annotations

from collections.abc import Iterable

from data_platform.processing.policies.policy import Policy
from data_platform.processing.policies.policy_context import PolicyContext
from data_platform.processing.policies.policy_result import PolicyResult


class PolicyManager:
    """
    Coordinates the evaluation of multiple execution policies.
    """

    def __init__(
        self,
        policies: Iterable[Policy] | None = None,
    ) -> None:
        self._policies = tuple(
            policies or ()
        )

    @property
    def policies(
        self,
    ) -> tuple[Policy, ...]:
        """
        Registered policies.
        """

        return self._policies

    async def evaluate(
        self,
        context: PolicyContext,
    ) -> PolicyResult:
        """
        Evaluates all registered policies.

        Results are merged so multiple policies can
        contribute to the final execution decision.
        """

        continue_execution = True

        retry = False

        cancel_pipeline = False

        reason: str | None = None

        for policy in self._policies:
            result = await policy.evaluate(
                context,
            )

            continue_execution = (
                continue_execution
                and result.continue_execution
            )

            retry = retry or result.retry

            cancel_pipeline = (
                cancel_pipeline
                or result.cancel_pipeline
            )

            if (
                reason is None
                and result.reason is not None
            ):
                reason = result.reason

            if cancel_pipeline:
                break

        return PolicyResult(
            continue_execution=continue_execution,
            retry=retry,
            cancel_pipeline=cancel_pipeline,
            reason=reason,
        )