"""
Modern Data Platform
Processing Framework

Counter metric.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.metrics.metric_id import MetricId
from data_platform.processing.metrics.metric import Metric


class Counter(Metric):
    """
    Monotonically increasing metric.
    """

    def __init__(
        self,
        metric_id: MetricId,
        initial: int = 0,
    ) -> None:
        super().__init__(metric_id)

        if initial < 0:
            raise ValueError(
                "Counter cannot start with a negative value."
            )

        self._value = initial

    @property
    def value(self) -> int:
        return self._value

    def increment(
        self,
        amount: int = 1,
    ) -> None:
        if amount <= 0:
            raise ValueError(
                "Increment amount must be greater than zero."
            )

        self._value += amount

    def reset(self) -> None:
        self._value = 0

    def __int__(self) -> int:
        """
        Return the current counter value as an integer.
        """
        return self._value


    def __iadd__(
        self,
        value: int,
    ) -> "Counter":
        """
        Increment the counter using the += operator.
        """
        self.increment(value)
        return self