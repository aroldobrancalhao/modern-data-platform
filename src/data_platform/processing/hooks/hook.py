from __future__ import annotations

from abc import ABC, abstractmethod

from data_platform.processing.events.hook_context import HookContext


class Hook(ABC):
    """Base interface for processing framework hooks.

    Hooks are notified about lifecycle events emitted during pipeline
    execution. They enable cross-cutting concerns such as logging,
    metrics, statistics, tracing and auditing without coupling them
    to the processing framework.
    """

    @abstractmethod
    async def execute(self, context: HookContext) -> None:
        """Handle a lifecycle event."""