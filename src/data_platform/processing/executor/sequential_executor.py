"""
Modern Data Platform
Processing Framework

Sequential pipeline executor.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.processing_context import ProcessingContext
from data_platform.processing.core.stage_result import StageResult
from data_platform.processing.executor.base_executor import BaseExecutor


class SequentialExecutor(BaseExecutor):
    """
    Executes pipeline stages sequentially.

    Stages are executed in the same order they were
    defined in the Pipeline.
    """

    async def _execute_pipeline(
        self,
        pipeline: Pipeline,
        context: ProcessingContext,
        stage_results: list[StageResult],
    ) -> ExecutionStatus:

        for stage in pipeline:

            result = await stage.execute(context)

            stage_results.append(result)

            if result.failed:
                return ExecutionStatus.FAILED

        return ExecutionStatus.COMPLETED