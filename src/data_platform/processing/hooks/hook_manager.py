from __future__ import annotations

from collections import defaultdict

from data_platform.processing.events.hook_context import HookContext
from data_platform.processing.events.hook_type import HookType

from .hook import Hook


class HookManager:
    """Coordinates hook registration and event dispatching.

    The HookManager is responsible for maintaining the registered hooks
    and notifying them whenever a lifecycle event occurs.
    """

    def __init__(self) -> None:
        self._hooks: dict[HookType, list[Hook]] = defaultdict(list)

    def register(
        self,
        hook_type: HookType,
        hook: Hook,
    ) -> None:
        """Register a hook for a lifecycle event."""
        self._hooks[hook_type].append(hook)

    def unregister(
        self,
        hook_type: HookType,
        hook: Hook,
    ) -> None:
        """Remove a previously registered hook."""

        hooks = self._hooks.get(hook_type)

        if hooks is None:
            return

        if hook in hooks:
            hooks.remove(hook)

    def clear(self) -> None:
        """Remove all registered hooks."""
        self._hooks.clear()

    def get_hooks(
        self,
        hook_type: HookType,
    ) -> tuple[Hook, ...]:
        """Return all hooks registered for an event."""
        return tuple(self._hooks.get(hook_type, []))

    async def dispatch(
        self,
        context: HookContext,
    ) -> None:
        """Dispatch a lifecycle event to all registered hooks."""

        for hook in self._hooks.get(context.hook_type, []):
            await hook.execute(context)