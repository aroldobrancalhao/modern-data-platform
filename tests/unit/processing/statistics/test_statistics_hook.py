"""
Modern Data Platform
Processing Framework

Unit tests for StatisticsHook.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.execution_status import (
    ExecutionStatus,
)
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.core.processing_result import (
    ProcessingResult,
)
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult
from data_platform.processing.events.hook_context import HookContext
from data_platform.processing.events.hook_type import HookType
from data_platform.processing.statistics.statistics_hook import (
    StatisticsHook,
)

import pytest

pytestmark = pytest.mark.anyio


class DummyStage(Stage):
    """
    Simple stage used for testing.
    """

    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:
        return StageResult(
            status=ExecutionStatus.COMPLETED,
            metadata=context.metadata,
            stage_id=self.id,
            stage_name=self.name,
        )


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-1",
        metadata=ExecutionMetadata(
            execution_id="execution-1",
        ),
    )


def create_pipeline() -> Pipeline:
    return Pipeline(
        id="pipeline-1",
        name="Pipeline",
        stages=(
            DummyStage(
                id="extract",
                name="Extract",
            ),
            DummyStage(
                id="transform",
                name="Transform",
            ),
            DummyStage(
                id="load",
                name="Load",
            ),
        ),
    )


def create_result(
    context: ProcessingContext,
) -> ProcessingResult:
    return ProcessingResult(
        status=ExecutionStatus.COMPLETED,
        metadata=context.metadata,
    )


async def test_should_collect_statistics_for_completed_pipeline() -> None:
    hook = StatisticsHook()

    context = create_context()
    pipeline = create_pipeline()

    await hook.execute(
        HookContext(
            hook_type=HookType.BEFORE_PIPELINE,
            pipeline=pipeline,
            processing_context=context,
        )
    )

    for stage in pipeline.stages:
        await hook.execute(
            HookContext(
                hook_type=HookType.BEFORE_STAGE,
                pipeline=pipeline,
                processing_context=context,
                stage=stage,
            )
        )

        await hook.execute(
            HookContext(
                hook_type=HookType.AFTER_STAGE,
                pipeline=pipeline,
                processing_context=context,
                stage=stage,
                result=create_result(context),
            )
        )

    await hook.execute(
        HookContext(
            hook_type=HookType.AFTER_PIPELINE,
            pipeline=pipeline,
            processing_context=context,
        )
    )

    assert hook.statistics is not None

    pipeline_statistics = hook.statistics.pipeline

    assert pipeline_statistics.status == ExecutionStatus.COMPLETED
    assert pipeline_statistics.successful_stages == 3
    assert pipeline_statistics.failed_stages == 0
    assert pipeline_statistics.total_stages == 3
    assert len(pipeline_statistics.stage_statistics) == 3


async def test_should_collect_failed_stage() -> None:
    hook = StatisticsHook()

    context = create_context()
    pipeline = create_pipeline()

    stage = pipeline.stages[0]

    await hook.execute(
        HookContext(
            hook_type=HookType.BEFORE_PIPELINE,
            pipeline=pipeline,
            processing_context=context,
        )
    )

    await hook.execute(
        HookContext(
            hook_type=HookType.BEFORE_STAGE,
            pipeline=pipeline,
            processing_context=context,
            stage=stage,
        )
    )

    await hook.execute(
        HookContext(
            hook_type=HookType.STAGE_FAILED,
            pipeline=pipeline,
            processing_context=context,
            stage=stage,
            exception=RuntimeError(),
        )
    )

    await hook.execute(
        HookContext(
            hook_type=HookType.PIPELINE_FAILED,
            pipeline=pipeline,
            processing_context=context,
        )
    )

    assert hook.statistics is not None

    pipeline_statistics = hook.statistics.pipeline

    assert pipeline_statistics.status == ExecutionStatus.FAILED
    assert pipeline_statistics.successful_stages == 0
    assert pipeline_statistics.failed_stages == 1
    assert pipeline_statistics.total_stages == 1


async def test_should_preserve_stage_execution_order() -> None:
    hook = StatisticsHook()

    context = create_context()
    pipeline = create_pipeline()

    await hook.execute(
        HookContext(
            hook_type=HookType.BEFORE_PIPELINE,
            pipeline=pipeline,
            processing_context=context,
        )
    )

    for stage in pipeline.stages:
        await hook.execute(
            HookContext(
                hook_type=HookType.BEFORE_STAGE,
                pipeline=pipeline,
                processing_context=context,
                stage=stage,
            )
        )

        await hook.execute(
            HookContext(
                hook_type=HookType.AFTER_STAGE,
                pipeline=pipeline,
                processing_context=context,
                stage=stage,
                result=create_result(context),
            )
        )

    await hook.execute(
        HookContext(
            hook_type=HookType.AFTER_PIPELINE,
            pipeline=pipeline,
            processing_context=context,
        )
    )

    assert hook.statistics is not None

    assert [
        stage.stage.id
        for stage in hook.statistics.pipeline.stage_statistics
    ] == [
        "extract",
        "transform",
        "load",
    ]


async def test_should_store_execution_duration() -> None:
    hook = StatisticsHook()

    context = create_context()
    pipeline = create_pipeline()

    await hook.execute(
        HookContext(
            hook_type=HookType.BEFORE_PIPELINE,
            pipeline=pipeline,
            processing_context=context,
        )
    )

    await hook.execute(
        HookContext(
            hook_type=HookType.AFTER_PIPELINE,
            pipeline=pipeline,
            processing_context=context,
        )
    )

    assert hook.statistics is not None

    assert (
        hook.statistics.pipeline.finished_at
        >= hook.statistics.pipeline.started_at
    )

    assert hook.statistics.pipeline.duration.total_seconds() >= 0


async def test_should_reset_between_executions() -> None:
    hook = StatisticsHook()

    context = create_context()
    pipeline = create_pipeline()

    for _ in range(2):
        await hook.execute(
            HookContext(
                hook_type=HookType.BEFORE_PIPELINE,
                pipeline=pipeline,
                processing_context=context,
            )
        )

        await hook.execute(
            HookContext(
                hook_type=HookType.AFTER_PIPELINE,
                pipeline=pipeline,
                processing_context=context,
            )
        )

    assert hook.statistics is not None

    assert hook.statistics.pipeline.successful_stages == 0
    assert hook.statistics.pipeline.failed_stages == 0
    assert hook.statistics.pipeline.total_stages == 0


async def test_should_create_statistics_object() -> None:
    hook = StatisticsHook()

    context = create_context()
    pipeline = create_pipeline()

    await hook.execute(
        HookContext(
            hook_type=HookType.BEFORE_PIPELINE,
            pipeline=pipeline,
            processing_context=context,
        )
    )

    await hook.execute(
        HookContext(
            hook_type=HookType.AFTER_PIPELINE,
            pipeline=pipeline,
            processing_context=context,
        )
    )

    assert hook.statistics is not None
    assert hook.statistics.pipeline.pipeline == pipeline