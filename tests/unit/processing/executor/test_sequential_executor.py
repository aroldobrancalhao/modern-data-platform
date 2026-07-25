"""
Modern Data Platform
Processing Framework

Unit tests for SequentialExecutor.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.core.execution_metadata import ExecutionMetadata
from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.processing_context import ProcessingContext
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult
from data_platform.processing.executor.sequential_executor import (
    SequentialExecutor,
)

import pytest

pytestmark = pytest.mark.anyio

class SuccessfulStage(Stage):
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


class FailedStage(Stage):
    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:
        return StageResult(
            status=ExecutionStatus.FAILED,
            metadata=context.metadata,
            stage_id=self.id,
            stage_name=self.name,
            error_type="ValidationError",
            error_message="Stage failed.",
        )


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-1",
        metadata=ExecutionMetadata(
            execution_id="execution-1",
        ),
    )


def create_pipeline(*stages: Stage) -> Pipeline:
    return Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=tuple(stages),
    )


async def test_execute_single_stage_success() -> None:
    executor = SequentialExecutor()

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
    )

    result = await executor.execute(
        pipeline,
        create_context(),
    )

    assert result.status == ExecutionStatus.COMPLETED
    assert result.total_stages == 1
    assert result.successful_stages == 1
    assert result.failed_stages == 0
    assert result.has_failures is False


async def test_execute_multiple_stages_success() -> None:
    executor = SequentialExecutor()

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
        SuccessfulStage(
            id="transform",
            name="Transform",
        ),
        SuccessfulStage(
            id="load",
            name="Load",
        ),
    )

    result = await executor.execute(
        pipeline,
        create_context(),
    )

    assert result.status == ExecutionStatus.COMPLETED
    assert result.total_stages == 3
    assert result.successful_stages == 3
    assert result.failed_stages == 0
    assert result.last_result is not None
    assert result.last_result.stage_id == "load"


async def test_execute_stops_after_first_failure() -> None:
    executor = SequentialExecutor()

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
        FailedStage(
            id="transform",
            name="Transform",
        ),
        SuccessfulStage(
            id="load",
            name="Load",
        ),
    )

    result = await executor.execute(
        pipeline,
        create_context(),
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.total_stages == 2
    assert result.successful_stages == 1
    assert result.failed_stages == 1
    assert result.has_failures is True

    assert result.last_result is not None
    assert result.last_result.stage_id == "transform"


async def test_execute_propagates_stage_error() -> None:
    executor = SequentialExecutor()

    pipeline = create_pipeline(
        FailedStage(
            id="extract",
            name="Extract",
        ),
    )

    result = await executor.execute(
        pipeline,
        create_context(),
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.error_type == "ValidationError"
    assert result.error_message == "Stage failed."


async def test_execute_preserves_stage_results_order() -> None:
    executor = SequentialExecutor()

    pipeline = create_pipeline(
        SuccessfulStage(
            id="one",
            name="One",
        ),
        SuccessfulStage(
            id="two",
            name="Two",
        ),
        SuccessfulStage(
            id="three",
            name="Three",
        ),
    )

    result = await executor.execute(
        pipeline,
        create_context(),
    )

    assert [stage.stage_id for stage in result.stage_results] == [
        "one",
        "two",
        "three",
    ]


async def test_execute_preserves_metadata() -> None:
    context = create_context()

    executor = SequentialExecutor()

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
    )

    result = await executor.execute(
        pipeline,
        context,
    )

    assert result.metadata is context.metadata


async def test_execute_last_result_returns_failed_stage() -> None:
    executor = SequentialExecutor()

    pipeline = create_pipeline(
        SuccessfulStage(
            id="extract",
            name="Extract",
        ),
        FailedStage(
            id="transform",
            name="Transform",
        ),
    )

    result = await executor.execute(
        pipeline,
        create_context(),
    )

    assert result.last_result is not None
    assert result.last_result.stage_id == "transform"
    assert result.last_result.failed is True