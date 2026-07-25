from __future__ import annotations

from uuid import uuid4

import pytest

from data_platform.processing.core.execution_metadata import ExecutionMetadata
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.processing_context import ProcessingContext
from data_platform.processing.core.stage import Stage
from data_platform.processing.events.hook_context import HookContext
from data_platform.processing.events.hook_type import HookType
from data_platform.processing.hooks.hook import Hook
from data_platform.processing.hooks.hook_manager import HookManager


class DummyStage(Stage):
    async def execute(self, context: ProcessingContext):
        raise NotImplementedError


class DummyHook(Hook):
    async def execute(self, context: HookContext) -> None:
        pass


class RecordingHook(Hook):
    def __init__(self) -> None:
        self.calls: list[HookContext] = []

    async def execute(self, context: HookContext) -> None:
        self.calls.append(context)


def create_pipeline() -> Pipeline:
    return Pipeline(
        id="pipeline-1",
        name="Test Pipeline",
        stages=(
            DummyStage(
                id="stage-1",
                name="Stage 1",
            ),
        ),
    )


def create_processing_context() -> ProcessingContext:
    return ProcessingContext(
        id=str(uuid4()),
        metadata=ExecutionMetadata(
            execution_id=str(uuid4()),
        ),
    )


def create_hook_context(
    hook_type: HookType = HookType.BEFORE_PIPELINE,
) -> HookContext:
    return HookContext(
        hook_type=hook_type,
        pipeline=create_pipeline(),
        processing_context=create_processing_context(),
    )


def test_register_hook() -> None:
    manager = HookManager()

    hook = DummyHook()

    manager.register(HookType.BEFORE_STAGE, hook)

    assert manager.get_hooks(HookType.BEFORE_STAGE) == (hook,)


def test_register_multiple_hooks_preserves_order() -> None:
    manager = HookManager()

    hook1 = DummyHook()
    hook2 = DummyHook()
    hook3 = DummyHook()

    manager.register(HookType.BEFORE_STAGE, hook1)
    manager.register(HookType.BEFORE_STAGE, hook2)
    manager.register(HookType.BEFORE_STAGE, hook3)

    assert manager.get_hooks(HookType.BEFORE_STAGE) == (
        hook1,
        hook2,
        hook3,
    )


def test_unregister_hook() -> None:
    manager = HookManager()

    hook = DummyHook()

    manager.register(HookType.BEFORE_STAGE, hook)
    manager.unregister(HookType.BEFORE_STAGE, hook)

    assert manager.get_hooks(HookType.BEFORE_STAGE) == ()


def test_clear_removes_all_hooks() -> None:
    manager = HookManager()

    manager.register(HookType.BEFORE_STAGE, DummyHook())
    manager.register(HookType.AFTER_STAGE, DummyHook())
    manager.register(HookType.PIPELINE_FAILED, DummyHook())

    manager.clear()

    assert manager.get_hooks(HookType.BEFORE_STAGE) == ()
    assert manager.get_hooks(HookType.AFTER_STAGE) == ()
    assert manager.get_hooks(HookType.PIPELINE_FAILED) == ()


@pytest.mark.anyio
async def test_dispatch_executes_registered_hooks() -> None:
    manager = HookManager()

    hook1 = RecordingHook()
    hook2 = RecordingHook()

    manager.register(HookType.BEFORE_PIPELINE, hook1)
    manager.register(HookType.BEFORE_PIPELINE, hook2)

    context = create_hook_context()

    await manager.dispatch(context)

    assert hook1.calls == [context]
    assert hook2.calls == [context]


@pytest.mark.anyio
async def test_dispatch_only_executes_matching_hook_type() -> None:
    manager = HookManager()

    before_hook = RecordingHook()
    after_hook = RecordingHook()

    manager.register(HookType.BEFORE_PIPELINE, before_hook)
    manager.register(HookType.AFTER_PIPELINE, after_hook)

    context = create_hook_context(HookType.BEFORE_PIPELINE)

    await manager.dispatch(context)

    assert before_hook.calls == [context]
    assert after_hook.calls == []