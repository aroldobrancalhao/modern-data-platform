"""
Modern Data Platform
Processing Framework

Statistics hook.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from datetime import datetime

from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.events.hook_context import HookContext
from data_platform.processing.events.hook_type import HookType
from data_platform.processing.hooks.hook import Hook
from data_platform.processing.statistics.pipeline_statistics import (
    PipelineStatistics,
)
from data_platform.processing.statistics.stage_statistics import (
    StageStatistics,
)
from data_platform.processing.statistics.statistics import Statistics


class StatisticsHook(Hook):
    """
    Collects execution statistics from processing lifecycle events.
    """

    def __init__(self) -> None:
        self._statistics: Statistics | None = None

        self._pipeline_started_at: datetime | None = None

        self._pipeline_finished_at: datetime | None = None

        self._pipeline_status: ExecutionStatus = (
            ExecutionStatus.COMPLETED
        )

        self._stage_started: dict[str, datetime] = {}

        self._stage_statistics: list[StageStatistics] = []

        self._successful_stages = 0

        self._failed_stages = 0

    @property
    def statistics(self) -> Statistics | None:
        return self._statistics

    async def execute(
        self,
        context: HookContext,
    ) -> None:

        match context.hook_type:

            case HookType.BEFORE_PIPELINE:
                self._on_before_pipeline(context)

            case HookType.BEFORE_STAGE:
                self._on_before_stage(context)

            case HookType.AFTER_STAGE:
                self._on_after_stage(context)

            case HookType.STAGE_FAILED:
                self._on_stage_failed(context)

            case HookType.AFTER_PIPELINE:
                self._on_after_pipeline(context)

            case HookType.PIPELINE_FAILED:
                self._on_pipeline_failed(context)

    def _on_before_pipeline(
        self,
        context: HookContext,
    ) -> None:

        self._pipeline_started_at = context.timestamp

        self._pipeline_status = ExecutionStatus.COMPLETED

        self._successful_stages = 0

        self._failed_stages = 0

        self._stage_started.clear()

        self._stage_statistics.clear()

        self._statistics = None

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
            context.timestamp,
        )

        finished = context.timestamp

        self._stage_statistics.append(
            StageStatistics(
                stage=context.stage,
                status=ExecutionStatus.COMPLETED,
                started_at=started,
                finished_at=finished,
                duration=finished - started,
            )
        )

        self._successful_stages += 1

    def _on_stage_failed(
        self,
        context: HookContext,
    ) -> None:

        if context.stage is None:
            return

        started = self._stage_started.pop(
            context.stage.id,
            context.timestamp,
        )

        finished = context.timestamp

        self._stage_statistics.append(
            StageStatistics(
                stage=context.stage,
                status=ExecutionStatus.FAILED,
                started_at=started,
                finished_at=finished,
                duration=finished - started,
            )
        )

        self._failed_stages += 1

        self._pipeline_status = ExecutionStatus.FAILED

    def _on_after_pipeline(
        self,
        context: HookContext,
    ) -> None:

        if self._pipeline_started_at is None:
            return

        self._pipeline_finished_at = context.timestamp

        pipeline_statistics = PipelineStatistics(
            pipeline=context.pipeline,
            status=self._pipeline_status,
            started_at=self._pipeline_started_at,
            finished_at=self._pipeline_finished_at,
            duration=(
                self._pipeline_finished_at
                - self._pipeline_started_at
            ),
            successful_stages=self._successful_stages,
            failed_stages=self._failed_stages,
            stage_statistics=tuple(
                self._stage_statistics
            ),
        )

        self._statistics = Statistics(
            pipeline=pipeline_statistics,
        )

    def _on_pipeline_failed(
        self,
        context: HookContext,
    ) -> None:

        self._pipeline_status = ExecutionStatus.FAILED

        self._on_after_pipeline(context)