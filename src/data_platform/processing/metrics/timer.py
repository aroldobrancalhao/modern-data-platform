"""
Modern Data Platform
Processing Framework

Timer metric.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from statistics import mean

from data_platform.processing.metrics.metric import Metric
from data_platform.processing.metrics.metric_id import MetricId


class Timer(Metric):
    """
    Records execution durations.
    """

    def __init__(
        self,
        metric_id: MetricId,
    ) -> None:
        super().__init__(metric_id)
        self._durations: list[float] = []

    @property
    def average(self) -> float:
        """
        Average recorded duration.
        """
        if not self._durations:
            return 0.0

        return mean(self._durations)


    @property
    def value(self) -> float:
        """
        Compatibility property required by Metric.
        """
        return self.average

    @property
    def count(self) -> int:
        return len(self._durations)

    @property
    def total(self) -> float:
        return sum(self._durations)

    @property
    def minimum(self) -> float:
        if not self._durations:
            return 0.0

        return min(self._durations)

    @property
    def maximum(self) -> float:
        if not self._durations:
            return 0.0

        return max(self._durations)

    def record(
        self,
        duration: float,
    ) -> None:
        if duration < 0:
            raise ValueError(
                "Duration cannot be negative."
            )

        self._durations.append(float(duration))

    def reset(self) -> None:
        self._durations.clear()

    @property
    def empty(self) -> bool:
        """
        Whether the timer contains recorded durations.
        """
        return not self._durations