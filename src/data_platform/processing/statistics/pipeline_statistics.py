"""
Modern Data Platform
Processing Framework

Pipeline execution statistics.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta

from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.value_object import ValueObject
from data_platform.processing.statistics.stage_statistics import (
    StageStatistics,
)


@dataclass(
    frozen=True,
    eq=False,
    slots=True,
)
class PipelineStatistics(ValueObject):
    """
    Immutable execution statistics for an entire pipeline.
    """

    pipeline: Pipeline

    status: ExecutionStatus

    started_at: datetime

    finished_at: datetime

    duration: timedelta

    successful_stages: int

    failed_stages: int

    stage_statistics: tuple[StageStatistics, ...]

    def __post_init__(self) -> None:
        if self.finished_at < self.started_at:
            raise ValueError(
                "finished_at cannot be earlier than started_at."
            )

        if self.duration.total_seconds() < 0:
            raise ValueError(
                "duration cannot be negative."
            )

        if self.successful_stages < 0:
            raise ValueError(
                "successful_stages cannot be negative."
            )

        if self.failed_stages < 0:
            raise ValueError(
                "failed_stages cannot be negative."
            )

        if (
            self.successful_stages + self.failed_stages
            > len(self.stage_statistics)
        ):
            raise ValueError(
                "Stage counters exceed collected statistics."
            )

    @property
    def total_stages(self) -> int:
        return len(self.stage_statistics)

    @property
    def has_failures(self) -> bool:
        return self.failed_stages > 0

    @property
    def success_rate(self) -> float:
        if self.total_stages == 0:
            return 0.0

        return self.successful_stages / self.total_stages