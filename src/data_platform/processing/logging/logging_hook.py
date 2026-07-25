"""
Modern Data Platform
Processing Framework

Logging hook.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.events.hook_context import HookContext
from data_platform.processing.events.hook_type import HookType
from data_platform.processing.hooks.hook import Hook
from data_platform.processing.logging.console_logger import ConsoleLogger
from data_platform.processing.logging.log_entry import LogEntry
from data_platform.processing.logging.log_level import LogLevel
from data_platform.processing.logging.logger import Logger


class LoggingHook(Hook):
    """
    Logs pipeline lifecycle events.
    """

    def __init__(
        self,
        logger: Logger | None = None,
    ) -> None:
        self._logger = logger or ConsoleLogger()

    @property
    def logger(self) -> Logger:
        return self._logger

    async def execute(
        self,
        context: HookContext,
    ) -> None:

        match context.hook_type:

            case HookType.BEFORE_PIPELINE:
                self._before_pipeline(context)

            case HookType.AFTER_PIPELINE:
                self._after_pipeline(context)

            case HookType.PIPELINE_FAILED:
                self._pipeline_failed(context)

            case HookType.BEFORE_STAGE:
                self._before_stage(context)

            case HookType.AFTER_STAGE:
                self._after_stage(context)

            case HookType.STAGE_FAILED:
                self._stage_failed(context)

    def _before_pipeline(
        self,
        context: HookContext,
    ) -> None:

        self._logger.log(
            LogEntry(
                level=LogLevel.INFO,
                message="Pipeline started.",
                execution_id=context.processing_context.metadata.execution_id,
                pipeline_id=context.pipeline.id,
                pipeline_name=context.pipeline.name,
            )
        )

    def _after_pipeline(
        self,
        context: HookContext,
    ) -> None:

        self._logger.log(
            LogEntry(
                level=LogLevel.INFO,
                message="Pipeline finished.",
                execution_id=context.processing_context.metadata.execution_id,
                pipeline_id=context.pipeline.id,
                pipeline_name=context.pipeline.name,
            )
        )

    def _pipeline_failed(
        self,
        context: HookContext,
    ) -> None:

        self._logger.log(
            LogEntry(
                level=LogLevel.ERROR,
                message="Pipeline failed.",
                execution_id=context.processing_context.metadata.execution_id,
                pipeline_id=context.pipeline.id,
                pipeline_name=context.pipeline.name,
                exception=context.exception,
            )
        )

    def _before_stage(
        self,
        context: HookContext,
    ) -> None:

        if context.stage is None:
            return

        self._logger.log(
            LogEntry(
                level=LogLevel.DEBUG,
                message="Stage started.",
                execution_id=context.processing_context.metadata.execution_id,
                pipeline_id=context.pipeline.id,
                pipeline_name=context.pipeline.name,
                stage_id=context.stage.id,
                stage_name=context.stage.name,
            )
        )

    def _after_stage(
        self,
        context: HookContext,
    ) -> None:

        if context.stage is None:
            return

        self._logger.log(
            LogEntry(
                level=LogLevel.DEBUG,
                message="Stage finished.",
                execution_id=context.processing_context.metadata.execution_id,
                pipeline_id=context.pipeline.id,
                pipeline_name=context.pipeline.name,
                stage_id=context.stage.id,
                stage_name=context.stage.name,
            )
        )

    def _stage_failed(
        self,
        context: HookContext,
    ) -> None:

        if context.stage is None:
            return

        self._logger.log(
            LogEntry(
                level=LogLevel.ERROR,
                message="Stage failed.",
                execution_id=context.processing_context.metadata.execution_id,
                pipeline_id=context.pipeline.id,
                pipeline_name=context.pipeline.name,
                stage_id=context.stage.id,
                stage_name=context.stage.name,
                exception=context.exception,
            )
        )