"""
Modern Data Platform
Processing Framework

Unit tests for LoggingHook.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

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
from data_platform.processing.core.stage_result import (
    StageResult,
)
from data_platform.processing.events.hook_context import (
    HookContext,
)
from data_platform.processing.events.hook_type import (
    HookType,
)
from data_platform.processing.logging.logger import Logger
from data_platform.processing.logging.logging_hook import (
    LoggingHook,
)

pytestmark = pytest.mark.anyio


class DummyStage(Stage):

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
        id="context",
        metadata=ExecutionMetadata(
            execution_id="execution-1",
        ),
    )


def create_pipeline() -> Pipeline:
    return Pipeline(
        id="pipeline",
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
        ),
    )


def create_result(
    context: ProcessingContext,
) -> ProcessingResult:
    return ProcessingResult(
        status=ExecutionStatus.COMPLETED,
        metadata=context.metadata,
    )


async def test_should_log_pipeline_execution() -> None:

    logger = Mock(spec=Logger)

    hook = LoggingHook(
        logger=logger,
    )

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

    assert logger.log.call_count == 6


async def test_should_log_stage_failure() -> None:

    logger = Mock(spec=Logger)

    hook = LoggingHook(
        logger=logger,
    )

    context = create_context()

    pipeline = create_pipeline()

    stage = pipeline.stages[0]

    await hook.execute(
        HookContext(
            hook_type=HookType.STAGE_FAILED,
            pipeline=pipeline,
            processing_context=context,
            stage=stage,
            exception=RuntimeError(),
        )
    )

    logger.log.assert_called_once()


async def test_should_log_pipeline_failure() -> None:

    logger = Mock(spec=Logger)

    hook = LoggingHook(
        logger=logger,
    )

    context = create_context()

    pipeline = create_pipeline()

    await hook.execute(
        HookContext(
            hook_type=HookType.PIPELINE_FAILED,
            pipeline=pipeline,
            processing_context=context,
            exception=RuntimeError(),
        )
    )

    logger.log.assert_called_once()


async def test_should_expose_logger() -> None:

    logger = Mock(spec=Logger)

    hook = LoggingHook(
        logger=logger,
    )

    assert hook.logger is logger


async def test_should_log_multiple_pipeline_executions() -> None:

    logger = Mock(spec=Logger)

    hook = LoggingHook(
        logger=logger,
    )

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

    assert logger.log.call_count == 4