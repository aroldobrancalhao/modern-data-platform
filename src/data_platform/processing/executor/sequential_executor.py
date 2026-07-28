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
from data_platform.processing.policies.policy_event import PolicyEvent
from data_platform.processing.runtime.execution_runtime import (
    ExecutionRuntime,
)


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

        runtime = ExecutionRuntime(context)

        runtime.execution_started()

        await self._emit_before_pipeline(
            pipeline=pipeline,
            processing_context=context,
        )

        has_tolerated_failures = False

        for stage in pipeline:

            runtime.stage_started(
                stage.id,
            )

            runtime.max_attempts(
                stage.max_attempts,
            )

            await self._emit_before_stage(
                pipeline=pipeline,
                processing_context=context,
                stage=stage,
            )

            attempt = 1

            while True:

                try:

                    result = await self._execute_stage(
                        stage=stage,
                        context=context,
                    )

                except Exception as exc:

                    runtime.stage_failed(
                        exc,
                    )

                    await self._emit_stage_failed(
                        pipeline=pipeline,
                        processing_context=context,
                        stage=stage,
                        exception=exc,
                    )

                    policy_result = await self._evaluate_policies(
                        processing_context=context,
                        pipeline=pipeline,
                        stage=stage,
                        event=PolicyEvent.STAGE_FAILED,
                    )

                    if policy_result.retry:

                        attempt += 1

                        runtime.retry_started(
                            attempt,
                        )

                        continue

                    runtime.execution_failed(
                        exc,
                    )

                    runtime.stage_finished()

                    await self._emit_pipeline_failed(
                        pipeline=pipeline,
                        processing_context=context,
                        exception=exc,
                    )

                    raise

                runtime.stage_result(
                    result,
                )

                if result.succeeded:

                    stage_results.append(
                        result,
                    )

                    runtime.stage_finished()

                    await self._emit_after_stage(
                        pipeline=pipeline,
                        processing_context=context,
                        stage=stage,
                        result=result,
                    )

                    break

                await self._emit_stage_failed(
                    pipeline=pipeline,
                    processing_context=context,
                    stage=stage,
                    result=result,
                    exception=None,
                )

                policy_result = await self._evaluate_policies(
                    processing_context=context,
                    pipeline=pipeline,
                    stage=stage,
                    event=PolicyEvent.STAGE_FAILED,
                )

                stage_results.append(
                    result,
                )

                runtime.stage_finished()

                if policy_result.cancel_pipeline:

                    exception = RuntimeError(
                        "Pipeline cancelled by FailurePolicy.",
                    )

                    runtime.execution_failed(
                        exception,
                    )

                    await self._emit_pipeline_failed(
                        pipeline=pipeline,
                        processing_context=context,
                        exception=exception,
                    )

                    return ExecutionStatus.FAILED

                has_tolerated_failures = True

                break

        if has_tolerated_failures:
            runtime.execution_failed()
        else:
            runtime.execution_completed()

        await self._emit_after_pipeline(
            pipeline=pipeline,
            processing_context=context,
        )

        return (
            ExecutionStatus.FAILED
            if has_tolerated_failures
            else ExecutionStatus.COMPLETED
        )