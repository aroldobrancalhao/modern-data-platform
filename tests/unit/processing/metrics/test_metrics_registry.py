"""
Modern Data Platform
Processing Framework

Unit tests for MetricsRegistry.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import pytest

from data_platform.processing.metrics.counter import Counter
from data_platform.processing.metrics.metric_id import MetricId
from data_platform.processing.metrics.metrics_registry import (
    MetricsRegistry,
)


def test_should_create_empty_registry() -> None:
    registry = MetricsRegistry()

    assert len(registry) == 0
    assert registry.metrics == {}


def test_should_register_metric() -> None:
    registry = MetricsRegistry()

    metric = Counter(
        MetricId(
            name="records",
        )
    )

    returned = registry.register(metric)

    assert returned is metric
    assert len(registry) == 1


def test_should_return_existing_metric_when_registering_twice() -> None:
    registry = MetricsRegistry()

    metric = Counter(
        MetricId(
            name="records",
        )
    )

    first = registry.register(metric)
    second = registry.register(metric)

    assert first is second
    assert len(registry) == 1


def test_should_create_counter_once() -> None:
    registry = MetricsRegistry()

    metric_id = MetricId("counter")

    counter1 = registry.counter(metric_id)
    counter2 = registry.counter(metric_id)

    assert counter1 is counter2


def test_should_create_gauge_once() -> None:
    registry = MetricsRegistry()

    metric_id = MetricId("gauge")

    gauge1 = registry.gauge(metric_id)
    gauge2 = registry.gauge(metric_id)

    assert gauge1 is gauge2


def test_should_create_timer_once() -> None:
    registry = MetricsRegistry()

    metric_id = MetricId("timer")

    timer1 = registry.timer(metric_id)
    timer2 = registry.timer(metric_id)

    assert timer1 is timer2


def test_should_get_existing_metric() -> None:
    registry = MetricsRegistry()

    metric = registry.counter(
        MetricId("records")
    )

    found = registry.get(metric.id)

    assert found is metric


def test_should_return_none_for_unknown_metric() -> None:
    registry = MetricsRegistry()

    assert (
        registry.get(
            MetricId("unknown")
        )
        is None
    )


def test_should_support_contains() -> None:
    registry = MetricsRegistry()

    metric = registry.counter(
        MetricId("records")
    )

    assert metric.id in registry


def test_should_return_metric_values() -> None:
    registry = MetricsRegistry()

    counter = registry.counter(
        MetricId("counter")
    )

    gauge = registry.gauge(
        MetricId("gauge")
    )

    values = registry.values()

    assert counter in values
    assert gauge in values
    assert len(values) == 2


def test_should_return_metric_items() -> None:
    registry = MetricsRegistry()

    metric = registry.counter(
        MetricId("counter")
    )

    items = registry.items()

    assert len(items) == 1

    metric_id, returned = items[0]

    assert metric_id == metric.id
    assert returned is metric


def test_should_clear_registry() -> None:
    registry = MetricsRegistry()

    registry.counter(
        MetricId("counter")
    )

    registry.gauge(
        MetricId("gauge")
    )

    registry.clear()

    assert len(registry) == 0


def test_should_reset_all_metrics() -> None:
    registry = MetricsRegistry()

    counter = registry.counter(
        MetricId("counter")
    )

    gauge = registry.gauge(
        MetricId("gauge")
    )

    timer = registry.timer(
        MetricId("timer")
    )

    counter.increment()

    gauge.set(15)

    timer.record(2.5)

    registry.reset()

    assert counter.value == 0
    assert gauge.value == 0
    assert timer.value == 0


def test_should_raise_when_requesting_counter_for_existing_gauge() -> None:
    registry = MetricsRegistry()

    metric_id = MetricId("metric")

    registry.gauge(metric_id)

    with pytest.raises(TypeError):
        registry.counter(metric_id)


def test_should_raise_when_requesting_gauge_for_existing_timer() -> None:
    registry = MetricsRegistry()

    metric_id = MetricId("metric")

    registry.timer(metric_id)

    with pytest.raises(TypeError):
        registry.gauge(metric_id)


def test_should_raise_when_requesting_timer_for_existing_counter() -> None:
    registry = MetricsRegistry()

    metric_id = MetricId("metric")

    registry.counter(metric_id)

    with pytest.raises(TypeError):
        registry.timer(metric_id)