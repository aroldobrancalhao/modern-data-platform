"""
Modern Data Platform
Processing Framework

Unit tests for FailurePolicy.
"""

from __future__ import annotations

import pytest

from data_platform.processing.core.context_keys import (
    ProcessingKeys,
)
from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.execution_status import (
    ExecutionStatus,
)
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.core.pipeline import (
    Pipeline,
)
from data_platform.processing.core.stage import (
    Stage,
)
from data_platform.processing.core.stage_result import (
    StageResult,
)
from data_platform.processing.policies.failure_policy import (
    FailurePolicy,
)
from data_platform.processing.policies.policy_context import (
    PolicyContext,
)
from data_platform.processing.policies.policy_event import (
    PolicyEvent,
)

pytestmark = pytest.mark.anyio


class DummyStage(Stage):

    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:
        raise NotImplementedError


def create_stage() -> Stage:
    return DummyStage(
        id="extract",
        name="Extract",
    )


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context",
        metadata=ExecutionMetadata(
            execution_id="execution",
        ),
    )


def create_pipeline() -> Pipeline:
    return Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(
            create_stage(),
        ),
    )


def create_policy_context(
    context: ProcessingContext,
    *,
    event: PolicyEvent,
) -> PolicyContext:
    pipeline = create_pipeline()

    return PolicyContext(
        processing_context=context,
        pipeline=pipeline,
        stage=pipeline.stages[0],
        event=event,
    )


async def test_should_ignore_other_events() -> None:
    policy = FailurePolicy()

    result = await policy.evaluate(
        create_policy_context(
            create_context(),
            event=PolicyEvent.BEFORE_STAGE,
        ),
    )

    assert result.continue_execution is True
    assert result.retry is False
    assert result.cancel_pipeline is False
    assert result.reason is None


async def test_should_ignore_technical_exception() -> None:
    policy = FailurePolicy()

    context = create_context()

    context.set(
        ProcessingKeys.EXCEPTION,
        RuntimeError(),
    )

    result = await policy.evaluate(
        create_policy_context(
            context,
            event=PolicyEvent.STAGE_FAILED,
        ),
    )

    assert result.continue_execution is True
    assert result.retry is False
    assert result.cancel_pipeline is False
    assert result.reason is None


async def test_should_cancel_pipeline_when_business_failure() -> None:
    policy = FailurePolicy()

    context = create_context()

    context.set(
        ProcessingKeys.STAGE_RESULT,
        StageResult(
            status=ExecutionStatus.FAILED,
            metadata=context.metadata,
            stage_id="extract",
            stage_name="Extract",
        ),
    )

    result = await policy.evaluate(
        create_policy_context(
            context,
            event=PolicyEvent.STAGE_FAILED,
        ),
    )

    assert result.continue_execution is False
    assert result.retry is False
    assert result.cancel_pipeline is True
    assert (
        result.reason
        == "Pipeline interrupted due to stage failure."
    )


async def test_should_continue_when_fail_fast_disabled() -> None:
    policy = FailurePolicy(
        fail_fast=False,
    )

    context = create_context()

    context.set(
        ProcessingKeys.STAGE_RESULT,
        StageResult(
            status=ExecutionStatus.FAILED,
            metadata=context.metadata,
            stage_id="extract",
            stage_name="Extract",
        ),
    )

    result = await policy.evaluate(
        create_policy_context(
            context,
            event=PolicyEvent.STAGE_FAILED,
        ),
    )

    assert result.continue_execution is True
    assert result.retry is False
    assert result.cancel_pipeline is False
    assert (
        result.reason
        == "Stage failure ignored by policy."
    )