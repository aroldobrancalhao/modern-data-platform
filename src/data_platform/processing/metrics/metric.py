"""
Modern Data Platform
Processing Framework

Base abstraction for metrics.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from collections.abc import Mapping
from typing import Any

from data_platform.processing.metrics.metric_id import MetricId


class Metric(ABC):
    """
    Base class for all metrics.
    """

    def __init__(
        self,
        metric_id: MetricId,
    ) -> None:
        self._id = metric_id

    @property
    def id(self) -> MetricId:
        return self._id

    @property
    def name(self) -> str:
        return self._id.name

    @property
    def description(self) -> str:
        return self._id.description

    @property
    def tags(self) -> Mapping[str, str]:
        return self.id.tags_dict()
    
    @property
    @abstractmethod
    def value(self) -> Any:
        """
        Current metric value.
        """

    @abstractmethod
    def reset(self) -> None:
        """
        Reset metric state.
        """

    def __eq__(
        self,
        other: object,
    ) -> bool:
        if not isinstance(other, Metric):
            return False

        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"value={self.value!r})"
        )