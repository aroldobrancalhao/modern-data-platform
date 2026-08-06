"""
Modern Data Platform
Processing Framework

Parallel pipeline executor.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import asyncio

from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.pipeline import Pipeline, StageGroup
from data_platform.processing.core.processing_context import ProcessingContext
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult
from data_platform.processing.executor.base_executor import BaseExecutor
from data_platform.processing.policies.policy_event import PolicyEvent
from data_platform.processing.runtime.execution_runtime import (
    ExecutionRuntime,
)


class ParallelExecutor(BaseExecutor):
    """
    Executes each of Pipeline.groups as a unit: a lone Stage runs on
    its own, a StageGroup (nested tuple) runs its members
    concurrently via asyncio.gather. Units themselves still execute in
    sequence, in definition order.

    Concurrency safety within a group relies on two things holding for
    every Stage in it, by convention -- nothing here can verify
    either:

    - The stages are genuinely independent (no stage reads context
      state a sibling in the same group is expected to have written).
    - Any stage-specific output a caller needs back is returned via
      StageResult.output, not published into ProcessingContext through
      a ContextWriter -- a ContextWriter's shared, unnamespaced keys
      (e.g. StorageContextWriter's StorageKeys.URI) would collide the
      same way the old single-slot ExecutionRuntime state did (see
      execution_runtime.py's module docstring) if two concurrent
      stages in the same group both wrote through one. Runtime's own
      bookkeeping is already safe (ContextVar-isolated per stage's
      asyncio.Task); ContextWriters are a separate, still-open
      concern for anything grouped that uses one (see
      "ParallelExecutor implemented" in
      docs/architecture/roadmap-next-steps.md).

    Partial failure within a group: every stage in the group always
    runs to completion (asyncio.gather(..., return_exceptions=True) --
    no stage is ever cancelled mid-flight because a sibling failed,
    since siblings' side effects, e.g. an in-progress S3 upload, are
    not safe to abandon partway). "Cancel the pipeline" (FailurePolicy's
    default fail_fast=True, or an unhandled technical exception once
    RetryPolicy gives up on a stage) only ever stops the *next* group
    from starting -- it never reaches back to abort something already
    in flight.
    """

    async def _execute_pipeline(
        self,
        pipeline: Pipeline,
        context: ProcessingContext,
        runtime: ExecutionRuntime,
        stage_results: list[StageResult],
    ) -> ExecutionStatus:

        runtime.execution_started()

        await self._emit_before_pipeline(
            pipeline=pipeline,
            processing_context=context,
        )

        has_tolerated_failures = False

        for group in pipeline.groups:

            outcomes = await asyncio.gather(
                *(
                    self._run_stage(
                        stage,
                        pipeline=pipeline,
                        context=context,
                        runtime=runtime,
                    )
                    for stage in group
                ),
                return_exceptions=True,
            )

            group_cancelled = False

            technical_failure: BaseException | None = None

            for outcome in outcomes:

                if isinstance(outcome, BaseException):
                    # An unhandled technical exception, retries
                    # already exhausted inside _run_stage -- mirrors
                    # SequentialExecutor's own `raise` in the same
                    # situation. Every other stage in this group still
                    # ran to completion (return_exceptions=True), so
                    # their results are still recorded below; only the
                    # *next* group is what actually gets stopped.
                    if technical_failure is None:
                        technical_failure = outcome

                    continue

                result, cancel = outcome

                stage_results.append(result)

                if cancel:
                    group_cancelled = True

            if technical_failure is not None:

                runtime.execution_failed(
                    technical_failure
                    if isinstance(technical_failure, Exception)
                    else RuntimeError(str(technical_failure)),
                )

                await self._emit_pipeline_failed(
                    pipeline=pipeline,
                    processing_context=context,
                    exception=(
                        technical_failure
                        if isinstance(technical_failure, Exception)
                        else RuntimeError(str(technical_failure))
                    ),
                )

                raise technical_failure

            if group_cancelled:

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

            if any(result.failed for result in stage_results[-len(group) :]):
                has_tolerated_failures = True

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

    async def _run_stage(
        self,
        stage: Stage,
        *,
        pipeline: Pipeline,
        context: ProcessingContext,
        runtime: ExecutionRuntime,
    ) -> tuple[StageResult, bool]:
        """
        Runs one stage, including its own retry loop, to completion.

        Always runs inside its own asyncio.Task once submitted to
        asyncio.gather() by _execute_pipeline() above -- every
        ExecutionRuntime call here (stage_started, retry_started, ...)
        writes to ContextVars private to that Task's copy of the
        current context, invisible to whatever sibling stage is
        running concurrently in the same group (see
        execution_runtime.py).

        Returns ``(result, cancel_pipeline)`` instead of mutating
        shared state or raising for a business failure -- the caller
        aggregates every group member's outcome only after all of them
        have finished. An unhandled *technical* exception (retries
        exhausted) is the one case that still raises, deliberately:
        SequentialExecutor doesn't tolerate this either (see its own
        `raise` in the equivalent branch), and asyncio.gather with
        return_exceptions=True is exactly what lets the caller observe
        it without one stage's exception cancelling its still-running
        siblings.
        """

        runtime.stage_started(stage.id)

        runtime.max_attempts(stage.max_attempts)

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

                runtime.stage_finished()

                raise

            runtime.stage_result(
                result,
            )

            if result.succeeded:

                runtime.stage_finished()

                await self._emit_after_stage(
                    pipeline=pipeline,
                    processing_context=context,
                    stage=stage,
                    result=result,
                )

                return result, False

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

            runtime.stage_finished()

            return result, policy_result.cancel_pipeline
