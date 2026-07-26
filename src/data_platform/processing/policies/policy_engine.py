"""
Modern Data Platform
Processing Framework

Coordinates execution policy application.
"""

from __future__ import annotations

from data_platform.processing.events.hook_context import (
    HookContext,
)
from data_platform.processing.policies.policy_manager import (
    PolicyManager,
)
from data_platform.processing.policies.policy_result import (
    PolicyResult,
)


class PolicyEngine:
    """
    Coordinates execution policy application.

    The executor interacts only with this class instead of
    directly accessing PolicyManager.
    """

    def __init__(
        self,
        manager: PolicyManager | None = None,
    ) -> None:
        self._manager = manager or PolicyManager()

    @property
    def manager(self) -> PolicyManager:
        """
        Returns the configured policy manager.
        """

        return self._manager

    async def apply(
        self,
        context: HookContext,
    ) -> PolicyResult:
        """
        Applies all registered execution policies.
        """

        return await self._manager.evaluate(context)