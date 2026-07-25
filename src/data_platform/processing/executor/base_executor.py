"""
Modern Data Platform
Processing Framework

Base executor implementation.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.pipeline_result import PipelineResult
from data_platform.processing.core.processing_context import ProcessingContext
from data_platform.processing.core.stage_result import StageResult
from data_platform.processing.executor.executor import Executor


class BaseExecutor(Executor, ABC):
    """
    Base implementation for pipeline executors.

    Concrete executors are responsible only for the
    execution strategy. Common concerns such as exception
    handling and PipelineResult creation are centralized
    here.
    """

    async def execute(
        self,
        pipeline: Pipeline,
        context: ProcessingContext,
    ) -> PipelineResult:

        stage_results: list[StageResult] = []

        try:

            status = await self._execute_pipeline(
                pipeline=pipeline,
                context=context,
                stage_results=stage_results,
            )

            if status == ExecutionStatus.FAILED:

                last = stage_results[-1] if stage_results else None

                return PipelineResult(
                    status=ExecutionStatus.FAILED,
                    metadata=context.metadata,
                    stage_results=tuple(stage_results),
                    error_type=last.error_type if last else None,
                    error_message=last.error_message if last else None,
                )

            return PipelineResult(
                status=ExecutionStatus.COMPLETED,
                metadata=context.metadata,
                stage_results=tuple(stage_results),
            )

        except Exception as exc:

            return PipelineResult(
                status=ExecutionStatus.FAILED,
                metadata=context.metadata,
                stage_results=tuple(stage_results),
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

    @abstractmethod
    async def _execute_pipeline(
        self,
        pipeline: Pipeline,
        context: ProcessingContext,
        stage_results: list[StageResult],
    ) -> ExecutionStatus:
        """
        Executes the pipeline according to a concrete
        execution strategy.

        Returns
        -------
        ExecutionStatus
            Final execution status.
        """
        raise NotImplementedError