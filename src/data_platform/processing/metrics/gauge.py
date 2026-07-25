"""
Modern Data Platform
Processing Framework

Gauge metric.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.metrics.metric import Metric
from data_platform.processing.metrics.metric_id import MetricId


class Gauge(Metric):
    """
    Metric that represents a mutable value.
    """

    def __init__(
        self,
        metric_id: MetricId,
        initial: float = 0.0,
    ) -> None:
        super().__init__(metric_id)
        self._value = float(initial)

    @property
    def value(self) -> float:
        return self._value

    def set(
        self,
        value: float,
    ) -> None:
        self._value = float(value)

    def increase(
        self,
        amount: float = 1.0,
    ) -> None:
        self._value += float(amount)

    def decrease(
        self,
        amount: float = 1.0,
    ) -> None:
        self._value -= float(amount)

    def reset(self) -> None:
        self._value = 0.0

    def __float__(self) -> float:
        """
        Return the current gauge value.
        """
        return self._value