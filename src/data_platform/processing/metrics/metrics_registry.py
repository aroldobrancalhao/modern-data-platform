"""
Modern Data Platform
Processing Framework

Metrics registry.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.metrics.counter import Counter
from data_platform.processing.metrics.gauge import Gauge
from data_platform.processing.metrics.metric import Metric
from data_platform.processing.metrics.metric_id import MetricId
from data_platform.processing.metrics.timer import Timer


class MetricsRegistry:
    """
    Registry responsible for managing all metrics.

    Guarantees:

    - only one metric per MetricId
    - type consistency
    - reset of all metrics
    """

    def __init__(self) -> None:
        self._metrics: dict[MetricId, Metric] = {}

    @property
    def metrics(self) -> dict[MetricId, Metric]:
        return self._metrics

    def __len__(self) -> int:
        return len(self._metrics)

    def __contains__(
        self,
        metric_id: MetricId,
    ) -> bool:
        return metric_id in self._metrics

    def clear(self) -> None:
        self._metrics.clear()

    def get(
        self,
        metric_id: MetricId,
    ) -> Metric | None:
        return self._metrics.get(metric_id)

    def values(self) -> list[Metric]:
        return list(self._metrics.values())

    def items(
        self,
    ) -> list[tuple[MetricId, Metric]]:
        return list(self._metrics.items())

    def register(
        self,
        metric: Metric,
    ) -> Metric:
        existing = self._metrics.get(metric.id)

        if existing is not None:
            return existing

        self._metrics[metric.id] = metric

        return metric

    def counter(
        self,
        metric_id: MetricId,
    ) -> Counter:
        metric = self._metrics.get(metric_id)

        if metric is None:
            metric = Counter(metric_id)
            self._metrics[metric_id] = metric
            return metric

        if not isinstance(metric, Counter):
            raise TypeError(
                f"Metric '{metric_id.name}' is not a Counter."
            )

        return metric

    def gauge(
        self,
        metric_id: MetricId,
    ) -> Gauge:
        metric = self._metrics.get(metric_id)

        if metric is None:
            metric = Gauge(metric_id)
            self._metrics[metric_id] = metric
            return metric

        if not isinstance(metric, Gauge):
            raise TypeError(
                f"Metric '{metric_id.name}' is not a Gauge."
            )

        return metric

    def timer(
        self,
        metric_id: MetricId,
    ) -> Timer:
        metric = self._metrics.get(metric_id)

        if metric is None:
            metric = Timer(metric_id)
            self._metrics[metric_id] = metric
            return metric

        if not isinstance(metric, Timer):
            raise TypeError(
                f"Metric '{metric_id.name}' is not a Timer."
            )

        return metric

    def reset(self) -> None:
        for metric in self._metrics.values():
            metric.reset()