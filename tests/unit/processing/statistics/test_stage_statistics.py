"""
Modern Data Platform
Processing Framework

Unit tests for StageStatistics.

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

from data_platform.processing.core.execution_metadata import ExecutionMetadata
from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.processing_context import ProcessingContext
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult
from data_platform.processing.statistics.stage_statistics import (
    StageStatistics,
)


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
    Creates a test stage.
    """

    return DummyStage(
        id="extract",
        name="Extract",
    )


def create_context() -> ProcessingContext:
    """
    Creates a processing context.
    """

    return ProcessingContext(
        id="context-1",
        metadata=ExecutionMetadata(
            execution_id="execution-1",
        ),
    )


def test_should_create_stage_statistics() -> None:
    """
    Should create StageStatistics.
    """

    stage = create_stage()

    started_at = datetime.now(UTC)
    finished_at = started_at + timedelta(seconds=1)

    statistics = StageStatistics(
        stage=stage,
        status=ExecutionStatus.COMPLETED,
        started_at=started_at,
        finished_at=finished_at,
        duration=finished_at - started_at,
    )

    assert statistics.stage == stage
    assert statistics.status == ExecutionStatus.COMPLETED
    assert statistics.duration == timedelta(seconds=1)


def test_should_preserve_execution_information() -> None:
    """
    Should preserve execution information.
    """

    stage = create_stage()

    started_at = datetime.now(UTC)
    finished_at = started_at + timedelta(seconds=5)

    statistics = StageStatistics(
        stage=stage,
        status=ExecutionStatus.COMPLETED,
        started_at=started_at,
        finished_at=finished_at,
        duration=finished_at - started_at,
    )

    assert statistics.started_at == started_at
    assert statistics.finished_at == finished_at
    assert statistics.duration == timedelta(seconds=5)


def test_should_validate_duration() -> None:
    """
    Should reject negative duration.
    """

    stage = create_stage()

    started_at = datetime.now(UTC)

    with pytest.raises(
        ValueError,
        match="duration cannot be negative.",
    ):
        StageStatistics(
            stage=stage,
            status=ExecutionStatus.COMPLETED,
            started_at=started_at,
            finished_at=started_at,
            duration=timedelta(seconds=-1),
        )


def test_stage_statistics_is_immutable() -> None:
    """
    StageStatistics must be immutable.
    """

    stage = create_stage()

    started_at = datetime.now(UTC)
    finished_at = started_at + timedelta(seconds=1)

    statistics = StageStatistics(
        stage=stage,
        status=ExecutionStatus.COMPLETED,
        started_at=started_at,
        finished_at=finished_at,
        duration=finished_at - started_at,
    )

    with pytest.raises(FrozenInstanceError):
        cast(Any, statistics).status = ExecutionStatus.FAILED