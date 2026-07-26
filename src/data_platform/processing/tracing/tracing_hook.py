"""
Modern Data Platform
Processing Framework

Tracing hook.
"""

from __future__ import annotations

from datetime import UTC, datetime

from data_platform.processing.core.execution_status import (
    ExecutionStatus,
)
from data_platform.processing.events.hook_context import HookContext
from data_platform.processing.events.hook_type import HookType
from data_platform.processing.hooks.hook import Hook
from data_platform.processing.tracing.console_tracer import (
    ConsoleTracer,
)
from data_platform.processing.tracing.trace import Trace
from data_platform.processing.tracing.trace_span import TraceSpan
from data_platform.processing.tracing.tracer import Tracer


class TracingHook(Hook):
    """
    Collects execution traces.
    """

    def __init__(
        self,
        *,
        tracer: Tracer | None = None,
    ) -> None:
        self._tracer = tracer or ConsoleTracer()

        self._trace: Trace | None = None

        self._active_spans: dict[str, TraceSpan] = {}

        self._completed_spans: list[TraceSpan] = []

    @property
    def tracer(self) -> Tracer:
        return self._tracer

    async def execute(
        self,
        context: HookContext,
    ) -> None:

        match context.hook_type:

            case HookType.BEFORE_PIPELINE:
                self._before_pipeline(context)

            case HookType.BEFORE_STAGE:
                self._before_stage(context)

            case HookType.AFTER_STAGE:
                self._after_stage(context)

            case HookType.STAGE_FAILED:
                self._stage_failed(context)

            case HookType.PIPELINE_FAILED:
                self._pipeline_failed(context)

            case HookType.AFTER_PIPELINE:
                self._after_pipeline(context)

    def _before_pipeline(
        self,
        context: HookContext,
    ) -> None:

        self._completed_spans.clear()
        self._active_spans.clear()

        self._trace = Trace(
            execution_id=context.processing_context.metadata.execution_id,
            pipeline_id=context.pipeline.id,
            pipeline_name=context.pipeline.name,
            status=ExecutionStatus.RUNNING,
        )

    def _before_stage(
        self,
        context: HookContext,
    ) -> None:

        if context.stage is None:
            return

        self._active_spans[context.stage.id] = TraceSpan(
            stage_id=context.stage.id,
            stage_name=context.stage.name,
            status=ExecutionStatus.RUNNING,
        )

    def _after_stage(
        self,
        context: HookContext,
    ) -> None:

        if context.stage is None:
            return

        span = self._active_spans.pop(
            context.stage.id,
            None,
        )

        if span is None:
            return

        finished = datetime.now(UTC)

        self._completed_spans.append(
            TraceSpan(
                stage_id=span.stage_id,
                stage_name=span.stage_name,
                status=(
                    context.result.status
                    if context.result is not None
                    else ExecutionStatus.COMPLETED
                ),
                started_at=span.started_at,
                finished_at=finished,
                duration=(
                    finished - span.started_at
                ).total_seconds(),
            )
        )

    def _stage_failed(
        self,
        context: HookContext,
    ) -> None:

        if context.stage is None:
            return

        span = self._active_spans.pop(
            context.stage.id,
            None,
        )

        if span is None:
            return

        finished = datetime.now(UTC)

        self._completed_spans.append(
            TraceSpan(
                stage_id=span.stage_id,
                stage_name=span.stage_name,
                status=(
                    context.result.status
                    if context.result is not None
                    else ExecutionStatus.FAILED
                ),
                started_at=span.started_at,
                finished_at=finished,
                duration=(
                    finished - span.started_at
                ).total_seconds(),
                exception=(
                    str(context.exception)
                    if context.exception
                    else None
                ),
            )
        )

    def _pipeline_failed(
        self,
        context: HookContext,
    ) -> None:
        self._after_pipeline(context)

    def _after_pipeline(
        self,
        context: HookContext,
    ) -> None:

        if self._trace is None:
            return

        finished = datetime.now(UTC)

        trace = Trace(
            execution_id=self._trace.execution_id,
            pipeline_id=self._trace.pipeline_id,
            pipeline_name=self._trace.pipeline_name,
            status=(
                context.result.status
                if context.result is not None
                else ExecutionStatus.COMPLETED
            ),
            started_at=self._trace.started_at,
            finished_at=finished,
            duration=(
                finished - self._trace.started_at
            ).total_seconds(),
            exception=(
                str(context.exception)
                if context.exception is not None
                else None
            ),
            spans=tuple(self._completed_spans),
        )

        self._tracer.record(trace)

        self._trace = None

        self._active_spans.clear()

        self._completed_spans.clear()