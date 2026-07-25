"""
Modern Data Platform
Processing Framework

Metrics hook.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from datetime import datetime

from data_platform.processing.events.hook_context import HookContext
from data_platform.processing.events.hook_type import HookType
from data_platform.processing.hooks.hook import Hook
from data_platform.processing.metrics.metric_id import MetricId
from data_platform.processing.metrics.metrics_registry import MetricsRegistry


class MetricsHook(Hook):
    """
    Collects execution metrics from processing lifecycle events.
    """

    def __init__(
        self,
        registry: MetricsRegistry | None = None,
    ) -> None:

        self._registry = registry or MetricsRegistry()

        self._pipeline_timer = self._registry.timer(
            MetricId(
                name="pipeline.duration",
                description="Pipeline execution duration.",
            )
        )

        self._stage_timer = self._registry.timer(
            MetricId(
                name="stage.duration",
                description="Stage execution duration.",
            )
        )

        self._stage_counter = self._registry.counter(
            MetricId(
                name="stage.executions",
                description="Executed stages.",
            )
        )

        self._pipeline_started_at: datetime | None = None

        self._stage_started: dict[str, datetime] = {}

    @property
    def registry(self) -> MetricsRegistry:
        return self._registry

    async def execute(
        self,
        context: HookContext,
    ) -> None:

        match context.hook_type:

            case HookType.BEFORE_PIPELINE:
                self._on_before_pipeline(context)

            case HookType.AFTER_PIPELINE:
                self._on_after_pipeline(context)

            case HookType.PIPELINE_FAILED:
                self._on_after_pipeline(context)

            case HookType.BEFORE_STAGE:
                self._on_before_stage(context)

            case HookType.AFTER_STAGE:
                self._on_after_stage(context)

            case HookType.STAGE_FAILED:
                self._on_stage_failed(context)

    def reset(self) -> None:
        self._registry.reset()

        self._pipeline_started_at = None

        self._stage_started.clear()

    def _on_before_pipeline(
        self,
        context: HookContext,
    ) -> None:

        self._pipeline_started_at = context.timestamp

        self._stage_started.clear()

    def _on_after_pipeline(
        self,
        context: HookContext,
    ) -> None:

        if self._pipeline_started_at is None:
            return

        duration = (
            context.timestamp
            - self._pipeline_started_at
        ).total_seconds()

        self._pipeline_timer.record(duration)

        self._pipeline_started_at = None

    def _on_before_stage(
        self,
        context: HookContext,
    ) -> None:

        if context.stage is None:
            return

        self._stage_started[
            context.stage.id
        ] = context.timestamp

    def _on_after_stage(
        self,
        context: HookContext,
    ) -> None:

        if context.stage is None:
            return

        started = self._stage_started.pop(
            context.stage.id,
            None,
        )

        if started is None:
            return

        duration = (
            context.timestamp - started
        ).total_seconds()

        self._stage_timer.record(duration)

        self._stage_counter.increment()

    def _on_stage_failed(
        self,
        context: HookContext,
    ) -> None:

        self._on_after_stage(context)