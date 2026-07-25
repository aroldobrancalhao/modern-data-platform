from __future__ import annotations

from data_platform.processing.events.hook_context import HookContext
from data_platform.processing.hooks.hook import Hook


class DummyHook(Hook):
    """Simple hook used for testing."""

    async def execute(self, context: HookContext) -> None:
        self.context = context


def test_hook_can_be_subclassed() -> None:
    """Concrete implementations should inherit from Hook."""

    hook = DummyHook()

    assert isinstance(hook, Hook)