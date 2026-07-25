"""
Modern Data Platform
Processing Framework

Stage execution statistics.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta

from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.value_object import ValueObject


@dataclass(
    frozen=True,
    eq=False,
    slots=True,
)
class StageStatistics(ValueObject):
    """
    Immutable execution statistics for a single stage.
    """

    stage: Stage

    status: ExecutionStatus

    started_at: datetime

    finished_at: datetime

    duration: timedelta

    def __post_init__(self) -> None:
        if self.finished_at < self.started_at:
            raise ValueError(
                "finished_at cannot be earlier than started_at."
            )

        if self.duration.total_seconds() < 0:
            raise ValueError(
                "duration cannot be negative."
            )