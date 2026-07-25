"""
Modern Data Platform
Processing Framework

Unit tests for PipelineStatistics.

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
from data_platform.processing.core.processing_context import ProcessingContext
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult
from data_platform.processing.statistics.pipeline_statistics import (
    PipelineStatistics,
)
from data_platform.processing.statistics.stage_statistics import (
    StageStatistics,
)


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


def create_stage(identifier: str) -> DummyStage:
    return DummyStage(
        id=identifier,
        name=f"Stage {identifier}",
    )


def create_pipeline() -> Pipeline:
    return Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(
            create_stage("extract"),
            create_stage("transform"),
            create_stage("load"),
        ),
    )


def create_stage_statistics(
    identifier: str,
    status: ExecutionStatus = ExecutionStatus.COMPLETED,
) -> StageStatistics:
    stage = create_stage(identifier)

    started_at = datetime.now(UTC)
    finished_at = started_at + timedelta(seconds=1)

    return StageStatistics(
        stage=stage,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        duration=finished_at - started_at,
    )


def test_should_create_pipeline_statistics() -> None:
    stage_statistics = (
        create_stage_statistics("extract"),
        create_stage_statistics("transform"),
        create_stage_statistics("load"),
    )

    started_at = datetime.now(UTC)
    finished_at = started_at + timedelta(seconds=3)

    statistics = PipelineStatistics(
        pipeline=create_pipeline(),
        status=ExecutionStatus.COMPLETED,
        started_at=started_at,
        finished_at=finished_at,
        duration=finished_at - started_at,
        successful_stages=3,
        failed_stages=0,
        stage_statistics=stage_statistics,
    )

    assert statistics.status == ExecutionStatus.COMPLETED
    assert statistics.successful_stages == 3
    assert statistics.failed_stages == 0
    assert statistics.total_stages == 3


def test_should_calculate_success_rate() -> None:
    statistics = PipelineStatistics(
        pipeline=create_pipeline(),
        status=ExecutionStatus.COMPLETED,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        duration=timedelta(),
        successful_stages=2,
        failed_stages=1,
        stage_statistics=(
            create_stage_statistics("extract"),
            create_stage_statistics("transform"),
            create_stage_statistics(
                "load",
                ExecutionStatus.FAILED,
            ),
        ),
    )

    assert statistics.success_rate == pytest.approx(2 / 3)


def test_should_return_zero_success_rate_when_empty() -> None:
    statistics = PipelineStatistics(
        pipeline=create_pipeline(),
        status=ExecutionStatus.COMPLETED,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        duration=timedelta(),
        successful_stages=0,
        failed_stages=0,
        stage_statistics=(),
    )

    assert statistics.total_stages == 0
    assert statistics.success_rate == 0.0


def test_should_detect_failures() -> None:
    statistics = PipelineStatistics(
        pipeline=create_pipeline(),
        status=ExecutionStatus.FAILED,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        duration=timedelta(),
        successful_stages=2,
        failed_stages=1,
        stage_statistics=(
            create_stage_statistics("extract"),
            create_stage_statistics("transform"),
            create_stage_statistics(
                "load",
                ExecutionStatus.FAILED,
            ),
        ),
    )

    assert statistics.has_failures is True


def test_should_not_detect_failures() -> None:
    statistics = PipelineStatistics(
        pipeline=create_pipeline(),
        status=ExecutionStatus.COMPLETED,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        duration=timedelta(),
        successful_stages=3,
        failed_stages=0,
        stage_statistics=(
            create_stage_statistics("extract"),
            create_stage_statistics("transform"),
            create_stage_statistics("load"),
        ),
    )

    assert statistics.has_failures is False


def test_should_validate_stage_counters() -> None:
    with pytest.raises(
        ValueError,
        match="Stage counters exceed collected statistics.",
    ):
        PipelineStatistics(
            pipeline=create_pipeline(),
            status=ExecutionStatus.COMPLETED,
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
            duration=timedelta(),
            successful_stages=3,
            failed_stages=0,
            stage_statistics=(),
        )


def test_should_be_immutable() -> None:
    statistics = PipelineStatistics(
        pipeline=create_pipeline(),
        status=ExecutionStatus.COMPLETED,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        duration=timedelta(),
        successful_stages=0,
        failed_stages=0,
        stage_statistics=(),
    )

    with pytest.raises(FrozenInstanceError):
        cast(Any, statistics).status = ExecutionStatus.FAILED