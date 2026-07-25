"""
Modern Data Platform
Processing Framework

Unit tests for Statistics.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import cast

import pytest

from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.processing_context import ProcessingContext
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult
from data_platform.processing.statistics.pipeline_statistics import (
    PipelineStatistics,
)
from data_platform.processing.statistics.stage_statistics import (
    StageStatistics,
)
from data_platform.processing.statistics.statistics import Statistics


class DummyStage(Stage):
    """
    Stage used for testing.
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


def create_stage() -> DummyStage:
    """
    Creates a stage.
    """

    return DummyStage(
        id="extract",
        name="Extract",
    )


def create_pipeline() -> Pipeline:
    """
    Creates a valid pipeline.
    """

    return Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(
            create_stage(),
        ),
    )


def create_stage_statistics() -> StageStatistics:
    """
    Creates a valid StageStatistics.
    """

    stage = create_stage()

    started_at = datetime.now(UTC)
    finished_at = started_at + timedelta(seconds=5)

    return StageStatistics(
        stage=stage,
        status=ExecutionStatus.COMPLETED,
        started_at=started_at,
        finished_at=finished_at,
        duration=finished_at - started_at,
    )


def create_pipeline_statistics() -> PipelineStatistics:
    """
    Creates a valid PipelineStatistics.
    """

    stage_statistics = (
        create_stage_statistics(),
    )

    started_at = datetime.now(UTC)
    finished_at = started_at + timedelta(seconds=5)

    return PipelineStatistics(
        pipeline=create_pipeline(),
        status=ExecutionStatus.COMPLETED,
        started_at=started_at,
        finished_at=finished_at,
        duration=finished_at - started_at,
        successful_stages=1,
        failed_stages=0,
        stage_statistics=stage_statistics,
    )


def test_should_create_statistics() -> None:
    """
    Should create Statistics.
    """

    pipeline_statistics = create_pipeline_statistics()

    statistics = Statistics(
        pipeline=pipeline_statistics,
    )

    assert statistics.pipeline == pipeline_statistics


def test_should_expose_pipeline_statistics() -> None:
    """
    Should expose pipeline statistics.
    """

    statistics = Statistics(
        pipeline=create_pipeline_statistics(),
    )

    assert statistics.pipeline.status == ExecutionStatus.COMPLETED
    assert statistics.pipeline.successful_stages == 1
    assert statistics.pipeline.failed_stages == 0
    assert statistics.pipeline.total_stages == 1


def test_should_preserve_pipeline_duration() -> None:
    """
    Should preserve pipeline duration.
    """

    statistics = Statistics(
        pipeline=create_pipeline_statistics(),
    )

    assert statistics.pipeline.duration == timedelta(seconds=5)


def test_should_be_immutable() -> None:
    """
    Statistics must be immutable.
    """

    statistics = Statistics(
        pipeline=create_pipeline_statistics(),
    )

    with pytest.raises(FrozenInstanceError):
        cast(Any, statistics).pipeline = create_pipeline_statistics()