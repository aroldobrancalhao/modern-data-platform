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

        await self._emit_before_pipeline(
            pipeline=pipeline,
            processing_context=context,
        )

        try:

            for stage in pipeline:

                await self._emit_before_stage(
                    pipeline=pipeline,
                    processing_context=context,
                    stage=stage,
                )

                try:

                    result = await stage.execute(context)

                except Exception as exc:

                    await self._emit_stage_failed(
                        pipeline=pipeline,
                        processing_context=context,
                        stage=stage,
                        exception=exc,
                    )

                    await self._emit_pipeline_failed(
                        pipeline=pipeline,
                        processing_context=context,
                        exception=exc,
                    )

                    raise

                stage_results.append(result)

                if result.failed:

                    await self._emit_stage_failed(
                        pipeline=pipeline,
                        processing_context=context,
                        stage=stage,
                        result=result,
                    )

                    await self._emit_pipeline_failed(
                        pipeline=pipeline,
                        processing_context=context,
                        result=result,
                    )

                    return ExecutionStatus.FAILED

                await self._emit_after_stage(
                    pipeline=pipeline,
                    processing_context=context,
                    stage=stage,
                    result=result,
                )

            await self._emit_after_pipeline(
                pipeline=pipeline,
                processing_context=context,
            )

            return ExecutionStatus.COMPLETED

        except Exception:
            raise