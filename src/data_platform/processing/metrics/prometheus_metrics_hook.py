"""
Modern Data Platform
Processing Framework

Prometheus metrics hook.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from datetime import datetime

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, push_to_gateway

from data_platform.observability.metrics_settings import MetricsSettings
from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.events.hook_context import HookContext
from data_platform.processing.events.hook_type import HookType
from data_platform.processing.hooks.hook import Hook

_DURATION_BUCKETS = (
    0.05,
    0.1,
    0.25,
    0.5,
    1,
    2.5,
    5,
    10,
    30,
    60,
)


class PrometheusHook(Hook):
    """
    Collects execution metrics from processing lifecycle events and
    exposes them as Prometheus metrics.

    Replaces the old MetricsHook/StatisticsHook pair (in-process,
    home-grown MetricsRegistry -- never scraped by anything) with
    real prometheus_client instrumentation, bound to an injectable
    CollectorRegistry so every entry point that instantiates this
    hook can push its own isolated batch to the Pushgateway without
    mixing metrics across concurrent runs. Same shape as
    LoggingHook/TracingHook: an optional dependency defaulting to a
    ready-to-use instance.
    """

    def __init__(
        self,
        registry: CollectorRegistry | None = None,
    ) -> None:

        self._registry = registry or CollectorRegistry()

        self._pipeline_duration = Histogram(
            "mdp_pipeline_duration_seconds",
            "Pipeline execution duration.",
            labelnames=("pipeline_name", "status"),
            buckets=_DURATION_BUCKETS,
            registry=self._registry,
        )

        self._stage_duration = Histogram(
            "mdp_stage_duration_seconds",
            "Stage execution duration.",
            labelnames=("pipeline_name", "stage_name", "status"),
            buckets=_DURATION_BUCKETS,
            registry=self._registry,
        )

        self._stage_executions = Counter(
            "mdp_stage_executions_total",
            "Executed stages.",
            labelnames=("pipeline_name", "stage_name", "status"),
            registry=self._registry,
        )

        self._pipeline_last_run = Gauge(
            "mdp_pipeline_last_run_timestamp_seconds",
            "Timestamp of the last pipeline run, set when its metrics "
            "are pushed to the Pushgateway.",
            labelnames=("pipeline_name", "status"),
            registry=self._registry,
        )

        self._pipeline_started_at: dict[str, datetime] = {}

        self._stage_started: dict[str, datetime] = {}

        self._last_pipeline_status: dict[str, ExecutionStatus] = {}

    @property
    def registry(self) -> CollectorRegistry:
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
                self._on_pipeline_failed(context)

            case HookType.BEFORE_STAGE:
                self._on_before_stage(context)

            case HookType.AFTER_STAGE:
                self._on_after_stage(context)

            case HookType.STAGE_FAILED:
                self._on_stage_failed(context)

    def push(
        self,
        job: str,
        settings: MetricsSettings | None = None,
    ) -> None:
        """
        Pushes every metric collected so far to the Pushgateway,
        under grouping key job=<job>. Each call overwrites the
        previous batch pushed under the same job -- there is no
        accumulation across separate process runs (e.g. across DAG
        runs of the same task).

        mdp_pipeline_last_run_timestamp_seconds is set here, right
        before pushing, for every pipeline this hook observed --
        deliberately not set per-pipeline as pipelines finish, so its
        value always reflects "when was this batch last pushed"
        rather than each pipeline's own finish time.
        """

        for pipeline_name, status in self._last_pipeline_status.items():
            self._pipeline_last_run.labels(
                pipeline_name=pipeline_name,
                status=status.value.lower(),
            ).set_to_current_time()

        resolved_settings = settings or MetricsSettings()

        push_to_gateway(
            resolved_settings.pushgateway_url,
            job=job,
            registry=self._registry,
        )

    def _on_before_pipeline(
        self,
        context: HookContext,
    ) -> None:

        self._pipeline_started_at[context.pipeline.id] = context.timestamp

        self._stage_started.clear()

    def _on_after_pipeline(
        self,
        context: HookContext,
    ) -> None:

        started = self._pipeline_started_at.pop(context.pipeline.id, None)

        if started is None:
            return

        status = (
            context.result.status
            if context.result is not None
            else ExecutionStatus.COMPLETED
        )

        duration = (context.timestamp - started).total_seconds()

        self._pipeline_duration.labels(
            pipeline_name=context.pipeline.name,
            status=status.value.lower(),
        ).observe(duration)

        self._last_pipeline_status[context.pipeline.name] = status

    def _on_pipeline_failed(
        self,
        context: HookContext,
    ) -> None:
        self._on_after_pipeline(context)

    def _on_before_stage(
        self,
        context: HookContext,
    ) -> None:

        if context.stage is None:
            return

        self._stage_started[context.stage.id] = context.timestamp

    def _on_after_stage(
        self,
        context: HookContext,
    ) -> None:

        if context.stage is None:
            return

        started = self._stage_started.pop(context.stage.id, None)

        if started is None:
            return

        status = (
            context.result.status
            if context.result is not None
            else ExecutionStatus.COMPLETED
        )

        duration = (context.timestamp - started).total_seconds()

        labels = {
            "pipeline_name": context.pipeline.name,
            "stage_name": context.stage.name,
            "status": status.value.lower(),
        }

        self._stage_duration.labels(**labels).observe(duration)

        self._stage_executions.labels(**labels).inc()

    def _on_stage_failed(
        self,
        context: HookContext,
    ) -> None:
        self._on_after_stage(context)
