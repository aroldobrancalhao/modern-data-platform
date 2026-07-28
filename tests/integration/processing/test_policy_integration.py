"""
Modern Data Platform
Processing Framework

Integration tests for the Policy Engine <-> Executor wiring.

These tests exercise SequentialExecutor together with real Policy
implementations (RetryPolicy, FailurePolicy, TimeoutPolicy) combined
through a PolicyManager, per ADR-010 (Capability-Based Shared
Execution Context) and its Phase 2 roadmap item ("Policy Engine
integration").

Unlike the unit tests for each Policy in isolation (tests/unit/.../
policies/), the goal here is to validate the *contract* between the
executor and the policy layer: retry bookkeeping written to the
ProcessingContext (CURRENT_ATTEMPT / MAX_ATTEMPTS), how a merged
PolicyResult drives retry / cancel / continue decisions, and how
that decision is reflected back in the PipelineResult and in the
hooks that observe execution.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from data_platform.processing.core.context_keys.processing_keys import (
    ProcessingKeys,
)
from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult
from data_platform.processing.events.hook_context import HookContext
from data_platform.processing.events.hook_type import HookType
from data_platform.processing.executor.sequential_executor import (
    SequentialExecutor,
)
from data_platform.processing.hooks.hook import Hook
from data_platform.processing.policies.failure_policy import FailurePolicy
from data_platform.processing.policies.policy_manager import PolicyManager
from data_platform.processing.policies.retry_policy import RetryPolicy
from data_platform.processing.policies.timeout_policy import TimeoutPolicy

pytestmark = pytest.mark.anyio


# ----------------------------------------------------------------------
# Test doubles
# ----------------------------------------------------------------------


class SuccessfulStage(Stage):
    """Always completes successfully."""

    async def execute(self, context: ProcessingContext) -> StageResult:
        return StageResult(
            status=ExecutionStatus.COMPLETED,
            metadata=context.metadata,
            stage_id=self.id,
            stage_name=self.name,
            attempt=context.get(ProcessingKeys.CURRENT_ATTEMPT, 1),
        )


class BusinessFailureStage(Stage):
    """Always returns a failed StageResult without raising."""

    async def execute(self, context: ProcessingContext) -> StageResult:
        return StageResult(
            status=ExecutionStatus.FAILED,
            metadata=context.metadata,
            stage_id=self.id,
            stage_name=self.name,
            error_type="ValidationError",
            error_message="Business rule violated.",
            attempt=context.get(ProcessingKeys.CURRENT_ATTEMPT, 1),
        )


class AlwaysRaisingStage(Stage):
    """Always raises a technical exception."""

    async def execute(self, context: ProcessingContext) -> StageResult:
        raise ConnectionError("upstream service unavailable")


@dataclass(eq=False, slots=True)
class FlakyStage(Stage):
    """
    Raises a transient exception a fixed number of times, then
    succeeds. Used to validate RetryPolicy recovery.
    """

    fail_times: int = 2
    calls: int = 0

    async def execute(self, context: ProcessingContext) -> StageResult:
        self.calls += 1

        if self.calls <= self.fail_times:
            raise TimeoutError(
                f"transient failure on call #{self.calls}"
            )

        return StageResult(
            status=ExecutionStatus.COMPLETED,
            metadata=context.metadata,
            stage_id=self.id,
            stage_name=self.name,
            attempt=context.get(ProcessingKeys.CURRENT_ATTEMPT, 1),
        )


class RecordingHook(Hook):
    """Records every HookContext it receives, in order."""

    def __init__(self) -> None:
        self.contexts: list[HookContext] = []

    async def execute(self, context: HookContext) -> None:
        self.contexts.append(context)

    @property
    def event_types(self) -> list[HookType]:
        return [context.hook_type for context in self.contexts]


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def create_context(
    *,
    started_at: datetime | None = None,
) -> ProcessingContext:
    return ProcessingContext(
        id="context-1",
        metadata=ExecutionMetadata(
            execution_id="execution-1",
            started_at=started_at,
        ),
    )


def create_pipeline(*stages: Stage) -> Pipeline:
    return Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=tuple(stages),
    )


def register_all_hooks(
    executor: SequentialExecutor,
    hook: Hook,
) -> None:
    for hook_type in HookType:
        executor.register_hook(hook_type, hook)


# ----------------------------------------------------------------------
# Default behavior (no PolicyManager supplied) stays fail-fast
# ----------------------------------------------------------------------


class TestDefaultPolicyManagerIsFailFast:
    """
    BaseExecutor falls back to PolicyManager((FailurePolicy(),)) when
    no PolicyManager is supplied. This section locks down that this
    default preserves the pre-Policy-Engine behavior: the pipeline
    stops on the very first failure, whether it is a raised
    exception or a business-level failed StageResult.
    """

    async def test_stops_on_business_failure_without_configuring_any_policy(
        self,
    ) -> None:
        executor = SequentialExecutor()

        pipeline = create_pipeline(
            SuccessfulStage(id="extract", name="Extract"),
            BusinessFailureStage(id="transform", name="Transform"),
            SuccessfulStage(id="load", name="Load"),
        )

        result = await executor.execute(pipeline, create_context())

        assert result.status == ExecutionStatus.FAILED
        assert result.total_stages == 2
        assert result.successful_stages == 1
        assert result.failed_stages == 1
        assert result.last_result is not None
        assert result.last_result.stage_id == "transform"

    async def test_stops_on_raised_exception_without_configuring_any_policy(
        self,
    ) -> None:
        executor = SequentialExecutor()

        pipeline = create_pipeline(
            AlwaysRaisingStage(id="extract", name="Extract"),
            SuccessfulStage(id="load", name="Load"),
        )

        result = await executor.execute(pipeline, create_context())

        assert result.status == ExecutionStatus.FAILED
        assert result.error_type == "ConnectionError"
        assert result.error_message == "upstream service unavailable"
        # The failing stage never produced a StageResult to append.
        assert result.total_stages == 0

    async def test_never_retries_a_raised_exception_without_retry_policy(
        self,
    ) -> None:
        executor = SequentialExecutor()

        flaky = FlakyStage(
            id="extract",
            name="Extract",
            fail_times=1,
        )

        result = await executor.execute(
            create_pipeline(flaky),
            create_context(),
        )

        assert result.status == ExecutionStatus.FAILED
        assert flaky.calls == 1


# ----------------------------------------------------------------------
# RetryPolicy: recovers from technical failures
# ----------------------------------------------------------------------


class TestRetryPolicyIntegration:
    """
    RetryPolicy is exclusively responsible for exceptions raised
    during Stage execution (business failures are FailurePolicy's
    responsibility). It reads its retry budget from the
    ProcessingContext, which the executor populates per-stage from
    Stage.max_attempts.
    """

    async def test_recovers_after_transient_exceptions_within_max_attempts(
        self,
    ) -> None:
        executor = SequentialExecutor(
            policy_manager=PolicyManager(
                (RetryPolicy(), FailurePolicy())
            ),
        )

        flaky = FlakyStage(
            id="extract",
            name="Extract",
            fail_times=2,
            max_attempts=3,
        )

        result = await executor.execute(
            create_pipeline(flaky),
            create_context(),
        )

        assert result.status == ExecutionStatus.COMPLETED
        assert flaky.calls == 3
        assert result.total_stages == 1
        assert result.stage_results[0].attempt == 3

    async def test_stops_once_max_attempts_is_reached(
        self,
    ) -> None:
        executor = SequentialExecutor(
            policy_manager=PolicyManager(
                (RetryPolicy(), FailurePolicy())
            ),
        )

        flaky = FlakyStage(
            id="extract",
            name="Extract",
            fail_times=10,
            max_attempts=3,
        )

        result = await executor.execute(
            create_pipeline(flaky),
            create_context(),
        )

        assert result.status == ExecutionStatus.FAILED
        assert flaky.calls == 3
        assert result.error_type == "TimeoutError"

    async def test_stops_after_exhausting_retries_even_without_failure_policy(
        self,
    ) -> None:
        """
        RetryPolicy alone never requests cancellation - it just stops
        asking for a retry. The executor still treats an unresolved
        exception as terminal once no retry is requested, regardless
        of whether a FailurePolicy is configured.
        """

        executor = SequentialExecutor(
            policy_manager=PolicyManager((RetryPolicy(),)),
        )

        flaky = FlakyStage(
            id="extract",
            name="Extract",
            fail_times=10,
            max_attempts=2,
        )

        result = await executor.execute(
            create_pipeline(flaky),
            create_context(),
        )

        assert result.status == ExecutionStatus.FAILED
        assert flaky.calls == 2

    async def test_stage_max_attempts_is_propagated_to_the_context(
        self,
    ) -> None:
        observed_max_attempts: list[int] = []

        class ObservingStage(Stage):
            async def execute(
                self,
                context: ProcessingContext,
            ) -> StageResult:
                observed_max_attempts.append(
                    context.get(ProcessingKeys.MAX_ATTEMPTS)
                )
                return StageResult(
                    status=ExecutionStatus.COMPLETED,
                    metadata=context.metadata,
                    stage_id=self.id,
                    stage_name=self.name,
                )

        executor = SequentialExecutor(
            policy_manager=PolicyManager(
                (RetryPolicy(), FailurePolicy())
            ),
        )

        stage = ObservingStage(
            id="extract",
            name="Extract",
            max_attempts=7,
        )

        await executor.execute(
            create_pipeline(stage),
            create_context(),
        )

        assert observed_max_attempts == [7]

    async def test_current_attempt_increments_across_retries(
        self,
    ) -> None:
        observed_attempts: list[int] = []

        @dataclass(eq=False, slots=True)
        class AttemptTrackingStage(Stage):
            fail_times: int = 2
            calls: int = 0

            async def execute(
                self,
                context: ProcessingContext,
            ) -> StageResult:
                self.calls += 1

                observed_attempts.append(
                    context.get(ProcessingKeys.CURRENT_ATTEMPT)
                )

                if self.calls <= self.fail_times:
                    raise TimeoutError("transient")

                return StageResult(
                    status=ExecutionStatus.COMPLETED,
                    metadata=context.metadata,
                    stage_id=self.id,
                    stage_name=self.name,
                )

        executor = SequentialExecutor(
            policy_manager=PolicyManager(
                (RetryPolicy(), FailurePolicy())
            ),
        )

        stage = AttemptTrackingStage(
            id="extract",
            name="Extract",
            fail_times=2,
            max_attempts=3,
        )

        await executor.execute(
            create_pipeline(stage),
            create_context(),
        )

        assert observed_attempts == [1, 2, 3]

    async def test_current_attempt_is_cleared_after_execution(
        self,
    ) -> None:
        executor = SequentialExecutor(
            policy_manager=PolicyManager(
                (RetryPolicy(), FailurePolicy())
            ),
        )

        flaky = FlakyStage(
            id="extract",
            name="Extract",
            fail_times=1,
            max_attempts=3,
        )

        context = create_context()

        await executor.execute(
            create_pipeline(flaky),
            context,
        )

        assert not context.contains(ProcessingKeys.CURRENT_ATTEMPT)
        assert not context.contains(ProcessingKeys.CURRENT_STAGE)

    async def test_ignores_business_failures_leaves_them_to_failure_policy(
        self,
    ) -> None:
        """
        A business failure (StageResult.failed, no exception) must
        not be retried by RetryPolicy - only FailurePolicy governs
        that outcome.
        """

        calls = {"count": 0}

        class CountingBusinessFailureStage(Stage):
            async def execute(
                self,
                context: ProcessingContext,
            ) -> StageResult:
                calls["count"] += 1
                return StageResult(
                    status=ExecutionStatus.FAILED,
                    metadata=context.metadata,
                    stage_id=self.id,
                    stage_name=self.name,
                    error_type="ValidationError",
                    error_message="bad row",
                )

        executor = SequentialExecutor(
            policy_manager=PolicyManager(
                (RetryPolicy(), FailurePolicy())
            ),
        )

        await executor.execute(
            create_pipeline(
                CountingBusinessFailureStage(
                    id="extract",
                    name="Extract",
                    max_attempts=5,
                )
            ),
            create_context(),
        )

        assert calls["count"] == 1


    async def test_retry_clears_stage_result_from_previous_attempt(self,) -> None:
        observed: list[StageResult | None] = []

        @dataclass(eq=False, slots=True)
        class RetryAwareStage(Stage):
            calls: int = 0

            async def execute(
                self,
                context: ProcessingContext,
            ) -> StageResult:

                observed.append(
                    context.get(
                        ProcessingKeys.STAGE_RESULT,
                    )
                )

                self.calls += 1

                if self.calls == 1:
                    raise TimeoutError("temporary")

                return StageResult(
                    status=ExecutionStatus.COMPLETED,
                    metadata=context.metadata,
                    stage_id=self.id,
                    stage_name=self.name,
                )

        executor = SequentialExecutor(
            policy_manager=PolicyManager(
                (
                    RetryPolicy(),
                    FailurePolicy(),
                ),
            ),
        )

        stage = RetryAwareStage(
            id="extract",
            name="Extract",
            max_attempts=2,
        )

        await executor.execute(
            create_pipeline(stage),
            create_context(),
        )

        assert observed == [
            None,
            None,
        ]


    async def test_policy_manager_merges_retry_and_failure_decisions(
        self,
    ) -> None:

        executor = SequentialExecutor(
            policy_manager=PolicyManager(
                (
                    RetryPolicy(),
                    FailurePolicy(
                        fail_fast=False,
                    ),
                ),
            ),
        )

        flaky = FlakyStage(
            id="extract",
            name="Extract",
            fail_times=1,
            max_attempts=2,
        )

        result = await executor.execute(
            create_pipeline(
                flaky,
                SuccessfulStage(
                    id="load",
                    name="Load",
                ),
            ),
            create_context(),
        )

        assert result.status == ExecutionStatus.COMPLETED

        assert flaky.calls == 2

        assert result.total_stages == 2


    async def test_retry_does_not_emit_after_stage_before_success(
        self,
    ) -> None:

        executor = SequentialExecutor(
            policy_manager=PolicyManager(
                (
                    RetryPolicy(),
                    FailurePolicy(),
                ),
            ),
        )

        hook = RecordingHook()

        executor.register_hook(
            HookType.AFTER_STAGE,
            hook,
        )

        flaky = FlakyStage(
            id="extract",
            name="Extract",
            fail_times=2,
            max_attempts=3,
        )

        await executor.execute(
            create_pipeline(flaky),
            create_context(),
        )

        assert hook.event_types == [
            HookType.AFTER_STAGE,
        ]


    async def test_retry_does_not_change_next_stage_attempt(
        self,
    ) -> None:

        attempts: list[int] = []

        class CaptureStage(Stage):

            async def execute(
                self,
                context: ProcessingContext,
            ) -> StageResult:

                attempts.append(
                    context.get(
                        ProcessingKeys.CURRENT_ATTEMPT,
                    )
                )

                return StageResult(
                    status=ExecutionStatus.COMPLETED,
                    metadata=context.metadata,
                    stage_id=self.id,
                    stage_name=self.name,
                )

        executor = SequentialExecutor(
            policy_manager=PolicyManager(
                (
                    RetryPolicy(),
                    FailurePolicy(),
                ),
            ),
        )

        flaky = FlakyStage(
            id="extract",
            name="Extract",
            fail_times=1,
            max_attempts=2,
        )

        await executor.execute(
            create_pipeline(
                flaky,
                CaptureStage(
                    id="load",
                    name="Load",
                ),
            ),
            create_context(),
        )

        assert attempts == [
            1,
        ]


    async def test_retry_keeps_only_final_stage_result(
        self,
    ) -> None:

        executor = SequentialExecutor(
            policy_manager=PolicyManager(
                (
                    RetryPolicy(),
                    FailurePolicy(),
                ),
            ),
        )

        flaky = FlakyStage(
            id="extract",
            name="Extract",
            fail_times=2,
            max_attempts=3,
        )

        result = await executor.execute(
            create_pipeline(flaky),
            create_context(),
        )

        assert len(result.stage_results) == 1

        assert result.stage_results[0].attempt == 3


# ----------------------------------------------------------------------
# FailurePolicy: governs business failures
# ----------------------------------------------------------------------


class TestFailurePolicyIntegration:
    async def test_fail_fast_true_cancels_pipeline_on_business_failure(
        self,
    ) -> None:
        executor = SequentialExecutor(
            policy_manager=PolicyManager(
                (FailurePolicy(fail_fast=True),)
            ),
        )

        pipeline = create_pipeline(
            SuccessfulStage(id="extract", name="Extract"),
            BusinessFailureStage(id="transform", name="Transform"),
            SuccessfulStage(id="load", name="Load"),
        )

        result = await executor.execute(pipeline, create_context())

        assert result.status == ExecutionStatus.FAILED
        assert result.total_stages == 2
        assert result.error_type == "ValidationError"

    async def test_fail_fast_false_tolerates_failure_and_continues(
        self,
    ) -> None:
        executor = SequentialExecutor(
            policy_manager=PolicyManager(
                (FailurePolicy(fail_fast=False),)
            ),
        )

        pipeline = create_pipeline(
            SuccessfulStage(id="extract", name="Extract"),
            BusinessFailureStage(id="transform", name="Transform"),
            SuccessfulStage(id="load", name="Load"),
        )

        result = await executor.execute(pipeline, create_context())

        assert result.total_stages == 3
        assert result.successful_stages == 2
        assert result.failed_stages == 1
        assert result.has_failures is True

        assert result.status == ExecutionStatus.FAILED

    async def test_ignores_raised_exceptions_leaves_them_to_retry_policy(
        self,
    ) -> None:
        """
        FailurePolicy must not react to technical exceptions -
        RetryPolicy (or the executor's own fail-fast fallback) owns
        that decision instead.
        """

        executor = SequentialExecutor(
            policy_manager=PolicyManager(
                (FailurePolicy(fail_fast=False),)
            ),
        )

        pipeline = create_pipeline(
            AlwaysRaisingStage(id="extract", name="Extract"),
        )

        result = await executor.execute(pipeline, create_context())

        assert result.status == ExecutionStatus.FAILED
        assert result.error_type == "ConnectionError"


# ----------------------------------------------------------------------
# TimeoutPolicy
# ----------------------------------------------------------------------


class TestTimeoutPolicyIntegration:
    async def test_cancels_pipeline_once_elapsed_time_exceeds_timeout(
        self,
    ) -> None:
        executor = SequentialExecutor(
            policy_manager=PolicyManager((TimeoutPolicy(timeout=1),)),
        )

        started_at = datetime.now(UTC) - timedelta(seconds=30)

        pipeline = create_pipeline(
            BusinessFailureStage(id="extract", name="Extract"),
        )

        result = await executor.execute(
            pipeline,
            create_context(started_at=started_at),
        )

        assert result.status == ExecutionStatus.FAILED

    async def test_does_not_interfere_before_the_timeout(self) -> None:
        executor = SequentialExecutor(
            policy_manager=PolicyManager(
                (
                    TimeoutPolicy(timeout=3600),
                    FailurePolicy(fail_fast=False),
                )
            ),
        )

        started_at = datetime.now(UTC) - timedelta(seconds=1)

        pipeline = create_pipeline(
            BusinessFailureStage(id="extract", name="Extract"),
            SuccessfulStage(id="load", name="Load"),
        )

        result = await executor.execute(
            pipeline,
            create_context(started_at=started_at),
        )
        assert result.total_stages == 2


# ----------------------------------------------------------------------
# Hook visibility into policy-driven decisions
# ----------------------------------------------------------------------


class TestHooksObservePolicyDrivenFailures:
    async def test_stage_failed_hook_receives_the_result_for_business_failures(
        self,
    ) -> None:
        executor = SequentialExecutor()

        hook = RecordingHook()
        executor.register_hook(HookType.STAGE_FAILED, hook)

        pipeline = create_pipeline(
            BusinessFailureStage(id="extract", name="Extract"),
        )

        await executor.execute(pipeline, create_context())

        assert len(hook.contexts) == 1

        stage_failed_context = hook.contexts[0]

        assert stage_failed_context.result is not None
        assert stage_failed_context.result.error_type == (
            "ValidationError"
        )
        assert stage_failed_context.exception is None

    async def test_stage_failed_hook_receives_the_exception_for_technical_failures(
        self,
    ) -> None:
        executor = SequentialExecutor()

        hook = RecordingHook()
        executor.register_hook(HookType.STAGE_FAILED, hook)

        pipeline = create_pipeline(
            AlwaysRaisingStage(id="extract", name="Extract"),
        )

        await executor.execute(pipeline, create_context())

        assert len(hook.contexts) == 1

        stage_failed_context = hook.contexts[0]

        assert stage_failed_context.exception is not None
        assert isinstance(
            stage_failed_context.exception,
            ConnectionError,
        )

    async def test_stage_failed_fires_once_per_retried_attempt(
        self,
    ) -> None:
        executor = SequentialExecutor(
            policy_manager=PolicyManager(
                (RetryPolicy(), FailurePolicy())
            ),
        )

        hook = RecordingHook()
        executor.register_hook(HookType.STAGE_FAILED, hook)

        flaky = FlakyStage(
            id="extract",
            name="Extract",
            fail_times=2,
            max_attempts=3,
        )

        result = await executor.execute(
            create_pipeline(flaky),
            create_context(),
        )

        assert result.status == ExecutionStatus.COMPLETED
        # One STAGE_FAILED event per failed attempt, none for the
        # final, successful one.
        assert len(hook.contexts) == 2

    async def test_full_hook_order_on_fail_fast_business_failure(
        self,
    ) -> None:
        executor = SequentialExecutor()

        hook = RecordingHook()
        register_all_hooks(executor, hook)

        pipeline = create_pipeline(
            SuccessfulStage(id="extract", name="Extract"),
            BusinessFailureStage(id="transform", name="Transform"),
        )

        result = await executor.execute(pipeline, create_context())

        assert result.status == ExecutionStatus.FAILED

        assert hook.event_types == [
            HookType.BEFORE_PIPELINE,
            HookType.BEFORE_STAGE,
            HookType.AFTER_STAGE,
            HookType.BEFORE_STAGE,
            HookType.STAGE_FAILED,
            HookType.PIPELINE_FAILED,
        ]


    