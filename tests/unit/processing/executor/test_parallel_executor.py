"""
Modern Data Platform
Processing Framework

Unit tests for ParallelExecutor.

No real sleeps anywhere here -- every synchronization point (proving
real concurrency, proving groups run in sequence) uses asyncio.Barrier
or asyncio.Event, backed by asyncio.wait_for(timeout=...) so a broken
executor that secretly serialized a group deadlocks into a fast,
deterministic test failure instead of hanging or flaking on timing.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

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
from data_platform.processing.executor.parallel_executor import (
    ParallelExecutor,
)
from data_platform.processing.runtime.execution_runtime import (
    current_stage_id,
)

pytestmark = pytest.mark.anyio


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context",
        metadata=ExecutionMetadata(
            execution_id="execution",
        ),
    )


class SuccessfulStage(Stage):
    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:
        return StageResult(
            status=ExecutionStatus.COMPLETED,
            metadata=context.metadata,
            stage_id=self.id,
            stage_name=self.name,
        )


@dataclass(eq=False, slots=True, kw_only=True)
class RendezvousStage(Stage):
    """
    Waits on a shared asyncio.Barrier before doing anything else, then
    records what it observes as "the current stage" into a dict shared
    by every member of its group.

    Proves two things at once: real concurrency (the barrier only
    releases once every member has arrived -- a group secretly run one
    at a time would never reach that count, and wait_for's timeout
    turns that into a fast failure instead of a hang) and per-stage
    isolation (each instance can only ever record its own id against
    its own key -- a collision on shared runtime state would show up
    as a wrong value here, not just a crash).
    """

    barrier: asyncio.Barrier
    observed: dict[str, str]

    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:
        await asyncio.wait_for(self.barrier.wait(), timeout=5)

        self.observed[self.id] = current_stage_id() or ""

        return StageResult(
            status=ExecutionStatus.COMPLETED,
            metadata=context.metadata,
            stage_id=self.id,
            stage_name=self.name,
        )


async def test_a_group_runs_its_members_concurrently_and_isolated() -> None:
    observed: dict[str, str] = {}

    barrier = asyncio.Barrier(3)

    stages = tuple(
        RendezvousStage(
            id=f"stage-{i}",
            name=f"Stage {i}",
            barrier=barrier,
            observed=observed,
        )
        for i in range(3)
    )

    pipeline = Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(stages,),
    )

    result = await ParallelExecutor().execute(
        pipeline,
        create_context(),
    )

    assert result.status == ExecutionStatus.COMPLETED

    assert observed == {
        "stage-0": "stage-0",
        "stage-1": "stage-1",
        "stage-2": "stage-2",
    }


async def test_groups_execute_in_sequence() -> None:
    events: list[str] = []

    release = asyncio.Event()

    started = asyncio.Event()

    class BlockingStage(Stage):
        async def execute(
            self,
            context: ProcessingContext,
        ) -> StageResult:
            events.append(f"{self.id}:start")

            started.set()

            await asyncio.wait_for(release.wait(), timeout=5)

            events.append(f"{self.id}:end")

            return StageResult(
                status=ExecutionStatus.COMPLETED,
                metadata=context.metadata,
                stage_id=self.id,
                stage_name=self.name,
            )

    class ImmediateStage(Stage):
        async def execute(
            self,
            context: ProcessingContext,
        ) -> StageResult:
            events.append(f"{self.id}:ran")

            return StageResult(
                status=ExecutionStatus.COMPLETED,
                metadata=context.metadata,
                stage_id=self.id,
                stage_name=self.name,
            )

    pipeline = Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(
            BlockingStage(id="a", name="A"),
            ImmediateStage(id="b", name="B"),
        ),
    )

    task = asyncio.ensure_future(
        ParallelExecutor().execute(pipeline, create_context())
    )

    # Deterministic rendezvous instead of guessing how many scheduler
    # ticks it takes to reach BlockingStage's own code through
    # ParallelExecutor's/BaseExecutor's intermediate awaits (hook
    # dispatch, etc.) -- wait_for's timeout still turns a genuinely
    # broken executor into a fast failure, not a hang.
    await asyncio.wait_for(started.wait(), timeout=5)

    assert events == ["a:start"]

    release.set()

    result = await asyncio.wait_for(task, timeout=5)

    assert events == ["a:start", "a:end", "b:ran"]
    assert result.status == ExecutionStatus.COMPLETED


async def test_every_stage_in_a_group_completes_even_if_one_fails() -> None:
    ran: list[str] = []

    class OkStage(Stage):
        async def execute(
            self,
            context: ProcessingContext,
        ) -> StageResult:
            ran.append(self.id)

            return StageResult(
                status=ExecutionStatus.COMPLETED,
                metadata=context.metadata,
                stage_id=self.id,
                stage_name=self.name,
            )

    class FailingStage(Stage):
        async def execute(
            self,
            context: ProcessingContext,
        ) -> StageResult:
            ran.append(self.id)

            return StageResult(
                status=ExecutionStatus.FAILED,
                metadata=context.metadata,
                stage_id=self.id,
                stage_name=self.name,
                error_type="ValidationError",
                error_message="Business failure.",
            )

    pipeline = Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(
            (
                OkStage(id="a", name="A"),
                FailingStage(id="b", name="B"),
                OkStage(id="c", name="C"),
            ),
        ),
    )

    result = await ParallelExecutor().execute(
        pipeline,
        create_context(),
    )

    # Every stage in the group ran to completion, "b" failing didn't
    # cancel its still-running siblings.
    assert set(ran) == {"a", "b", "c"}

    # FailurePolicy's default fail_fast=True still cancels the
    # pipeline overall -- just never anything already in flight.
    assert result.status == ExecutionStatus.FAILED
    assert result.successful_stages == 2
    assert result.failed_stages == 1


async def test_cancel_stops_the_next_group_not_the_current_one() -> None:
    ran: list[str] = []

    class FailingStage(Stage):
        async def execute(
            self,
            context: ProcessingContext,
        ) -> StageResult:
            ran.append(self.id)

            return StageResult(
                status=ExecutionStatus.FAILED,
                metadata=context.metadata,
                stage_id=self.id,
                stage_name=self.name,
                error_type="ValidationError",
                error_message="Business failure.",
            )

    class RecordingStage(Stage):
        async def execute(
            self,
            context: ProcessingContext,
        ) -> StageResult:
            ran.append(self.id)

            return StageResult(
                status=ExecutionStatus.COMPLETED,
                metadata=context.metadata,
                stage_id=self.id,
                stage_name=self.name,
            )

    pipeline = Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(
            FailingStage(id="fails", name="Fails"),
            RecordingStage(id="never-runs", name="Never Runs"),
        ),
    )

    result = await ParallelExecutor().execute(
        pipeline,
        create_context(),
    )

    assert ran == ["fails"]
    assert result.status == ExecutionStatus.FAILED


async def test_retry_within_a_group_does_not_break_the_group() -> None:
    calls = {"count": 0}

    ran_sibling = asyncio.Event()

    class FlakyStage(Stage):
        async def execute(
            self,
            context: ProcessingContext,
        ) -> StageResult:
            calls["count"] += 1

            if calls["count"] == 1:
                raise RuntimeError("transient")

            return StageResult(
                status=ExecutionStatus.COMPLETED,
                metadata=context.metadata,
                stage_id=self.id,
                stage_name=self.name,
            )

    class SiblingStage(Stage):
        async def execute(
            self,
            context: ProcessingContext,
        ) -> StageResult:
            ran_sibling.set()

            return StageResult(
                status=ExecutionStatus.COMPLETED,
                metadata=context.metadata,
                stage_id=self.id,
                stage_name=self.name,
            )

    pipeline = Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(
            (
                FlakyStage(id="flaky", name="Flaky", max_attempts=3),
                SiblingStage(id="sibling", name="Sibling"),
            ),
        ),
    )

    result = await ParallelExecutor().execute(
        pipeline,
        create_context(),
    )

    assert ran_sibling.is_set()
    assert calls["count"] == 2
    assert result.status == ExecutionStatus.COMPLETED
    assert result.successful_stages == 2


async def test_unhandled_exception_after_retries_exhausted_fails_the_pipeline() -> (
    None
):
    class AlwaysFailsStage(Stage):
        async def execute(
            self,
            context: ProcessingContext,
        ) -> StageResult:
            raise RuntimeError("boom")

    pipeline = Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(
            AlwaysFailsStage(
                id="doomed",
                name="Doomed",
                max_attempts=1,
            ),
        ),
    )

    result = await ParallelExecutor().execute(
        pipeline,
        create_context(),
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.error_type == "RuntimeError"
    assert result.error_message == "boom"


async def test_a_lone_stage_behaves_like_a_1_member_group() -> None:
    pipeline = Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(
            SuccessfulStage(id="a", name="A"),
            SuccessfulStage(id="b", name="B"),
        ),
    )

    result = await ParallelExecutor().execute(
        pipeline,
        create_context(),
    )

    assert result.status == ExecutionStatus.COMPLETED
    assert result.successful_stages == 2
    assert {r.stage_id for r in result.stage_results} == {"a", "b"}
