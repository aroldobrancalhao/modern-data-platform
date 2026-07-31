"""
Modern Data Platform
Processing Framework

Base executor implementation.

Author: Modern Data Platform
License: MIT
"""

from abc import ABC, abstractmethod

from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.pipeline_result import PipelineResult
from data_platform.processing.core.processing_context import ProcessingContext
from data_platform.processing.core.processing_result import ProcessingResult
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult
from data_platform.processing.events.hook_context import HookContext
from data_platform.processing.events.hook_type import HookType
from data_platform.processing.executor.executor import Executor
from data_platform.processing.hooks.hook import Hook
from data_platform.processing.hooks.hook_manager import HookManager

from data_platform.processing.policies.failure_policy import FailurePolicy
from data_platform.processing.policies.policy_context import PolicyContext
from data_platform.processing.policies.policy_event import PolicyEvent
from data_platform.processing.policies.policy_manager import PolicyManager
from data_platform.processing.policies.policy_result import PolicyResult
from data_platform.processing.policies.retry_policy import RetryPolicy
from data_platform.processing.runtime.execution_runtime import ExecutionRuntime


class BaseExecutor(Executor, ABC):
    """
    Base implementation for pipeline executors.

    Concrete executors are responsible only for the
    execution strategy. Common concerns such as exception
    handling, PipelineResult creation and hook dispatching
    are centralized here.

    When no PolicyManager is injected, the default composition is
    PolicyManager((FailurePolicy(), RetryPolicy())): business-level
    failures (a FAILED StageResult with no exception) still stop the
    pipeline immediately, per FailurePolicy's default fail_fast=True,
    while raised exceptions are retried automatically -- up to each
    Stage's max_attempts -- before the pipeline is finally marked
    FAILED.
    """

    def __init__(
        self,
        policy_manager: PolicyManager | None = None,
    ) -> None:
        self._hook_manager = HookManager()

        self._policy_manager = (
            policy_manager
            if policy_manager is not None
            else PolicyManager(
                (
                    FailurePolicy(),
                    RetryPolicy(),
                )
            )
        )

    # ------------------------------------------------------------------
    # Hook registration
    # ------------------------------------------------------------------

    def register_hook(
        self,
        hook_type: HookType,
        hook: Hook,
    ) -> None:
        """Register a hook for a lifecycle event."""
        self._hook_manager.register(hook_type, hook)

    def register_hooks(
        self,
        hook: Hook,
    ) -> None:
        """
        Register the same hook for every lifecycle event.
        """
        for hook_type in HookType:
            self.register_hook(
                hook_type=hook_type,
                hook=hook,
            )

    def unregister_hook(
        self,
        hook_type: HookType,
        hook: Hook,
    ) -> None:
        """Remove a previously registered hook."""
        self._hook_manager.unregister(hook_type, hook)

    def clear_hooks(self) -> None:
        """Remove all registered hooks."""
        self._hook_manager.clear()

    # ------------------------------------------------------------------
    # Hook dispatch
    # ------------------------------------------------------------------

    async def _emit(
        self,
        hook_type: HookType,
        pipeline: Pipeline,
        processing_context: ProcessingContext,
        *,
        stage: Stage | None = None,
        result: ProcessingResult | None = None,
        exception: Exception | None = None,
    ) -> None:
        """Dispatch a lifecycle event."""

        await self._hook_manager.dispatch(
            HookContext(
                hook_type=hook_type,
                pipeline=pipeline,
                processing_context=processing_context,
                stage=stage,
                result=result,
                exception=exception,
            )
        )

    def _build_policy_context(
        self,
        *,
        processing_context: ProcessingContext,
        pipeline: Pipeline,
        event: PolicyEvent,
        stage: Stage | None = None,
    ) -> PolicyContext:
        """
        Creates the read model consumed by the Policy Engine.
        """

        return PolicyContext(
            processing_context=processing_context,
            pipeline=pipeline,
            stage=stage,
            event=event,
        )


    async def _evaluate_policies(
        self,
        *,
        processing_context: ProcessingContext,
        pipeline: Pipeline,
        event: PolicyEvent,
        stage: Stage | None = None,
    ) -> PolicyResult:
        """
        Evaluates all registered execution policies.
        """

        policy_context = self._build_policy_context(
            processing_context=processing_context,
            pipeline=pipeline,
            stage=stage,
            event=event,
        )

        return await self._policy_manager.evaluate(
            policy_context,
        )

    async def _emit_before_pipeline(
        self,
        pipeline: Pipeline,
        processing_context: ProcessingContext,
    ) -> None:
        await self._emit(
            HookType.BEFORE_PIPELINE,
            pipeline,
            processing_context,
        )

    async def _emit_after_pipeline(
        self,
        pipeline: Pipeline,
        processing_context: ProcessingContext,
    ) -> None:
        await self._emit(
            HookType.AFTER_PIPELINE,
            pipeline,
            processing_context,
        )

    async def _emit_pipeline_failed(
        self,
        pipeline: Pipeline,
        processing_context: ProcessingContext,
        *,
        result: ProcessingResult | None = None,
        exception: Exception | None = None,
    ) -> None:
        await self._emit(
            HookType.PIPELINE_FAILED,
            pipeline,
            processing_context,
            result=result,
            exception=exception,
        )

    async def _execute_stage(
        self,
        stage: Stage,
        context: ProcessingContext,
    ) -> StageResult:
        """
        Executes a stage.

        The default implementation simply delegates to the Stage.
        Specialized executors may override this behavior.
        """

        return await stage.execute(context)

    async def _emit_before_stage(
        self,
        pipeline: Pipeline,
        processing_context: ProcessingContext,
        stage: Stage,
    ) -> None:
        await self._emit(
            HookType.BEFORE_STAGE,
            pipeline,
            processing_context,
            stage=stage,
        )

    async def _emit_after_stage(
        self,
        pipeline: Pipeline,
        processing_context: ProcessingContext,
        stage: Stage,
        result: ProcessingResult,
    ) -> None:
        await self._emit(
            HookType.AFTER_STAGE,
            pipeline,
            processing_context,
            stage=stage,
            result=result,
        )

    async def _emit_stage_failed(
        self,
        pipeline: Pipeline,
        processing_context: ProcessingContext,
        stage: Stage,
        *,
        result: ProcessingResult | None = None,
        exception: Exception | None = None,
    ) -> None:
        await self._emit(
            HookType.STAGE_FAILED,
            pipeline,
            processing_context,
            stage=stage,
            result=result,
            exception=exception,
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(
        self,
        pipeline: Pipeline,
        context: ProcessingContext,
    ) -> PipelineResult:

        stage_results: list[StageResult] = []

        runtime = ExecutionRuntime(context)

        try:

            status = await self._execute_pipeline(
                pipeline=pipeline,
                context=context,
                runtime=runtime,
                stage_results=stage_results,
            )

            if status == ExecutionStatus.FAILED:

                last = stage_results[-1] if stage_results else None

                result = PipelineResult(
                    status=ExecutionStatus.FAILED,
                    metadata=context.metadata,
                    stage_results=tuple(stage_results),
                    error_type=last.error_type if last else None,
                    error_message=last.error_message if last else None,
                )

                runtime.pipeline_result(result)

                return result

            result = PipelineResult(
                status=ExecutionStatus.COMPLETED,
                metadata=context.metadata,
                stage_results=tuple(stage_results),
            )

            runtime.pipeline_result(result)

            return result

        except Exception as exc:

            result = PipelineResult(
                status=ExecutionStatus.FAILED,
                metadata=context.metadata,
                stage_results=tuple(stage_results),
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

            runtime.pipeline_result(result)

            return result

    @abstractmethod
    async def _execute_pipeline(
        self,
        pipeline: Pipeline,
        context: ProcessingContext,
        runtime: ExecutionRuntime,
        stage_results: list[StageResult],
    ) -> ExecutionStatus:
        """
        Executes the pipeline according to a concrete
        execution strategy.

        Parameters
        ----------
        runtime:
            The ExecutionRuntime instance created by ``execute()`` for
            this run. Concrete executors MUST use this instance --
            instead of creating their own -- so that stage-level and
            pipeline-level state are synchronized through the same
            writer.

        Returns
        -------
        ExecutionStatus
            Final execution status.
        """
        raise NotImplementedError