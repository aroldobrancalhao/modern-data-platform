"""
Modern Data Platform
Processing Framework

Unit tests for RetryPolicy.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.core.context_keys.processing_keys import (
    ProcessingKeys,
)
from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.pipeline import (
    Pipeline,
)
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.core.stage import (
    Stage,
)
from data_platform.processing.policies.policy_context import (
    PolicyContext,
)
from data_platform.processing.policies.policy_event import (
    PolicyEvent,
)
from data_platform.processing.policies.retry_policy import (
    RetryPolicy,
)

import pytest

pytestmark = pytest.mark.anyio


class DummyStage(Stage):
    async def execute(
        self,
        context: ProcessingContext,
    ):
        raise NotImplementedError


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context",
        metadata=ExecutionMetadata(
            execution_id="execution-1",
        ),
    )


def create_pipeline() -> Pipeline:
    return Pipeline(
        id="pipeline",
        name="Pipeline",
        stages=(
            DummyStage(
                id="stage",
                name="Stage",
            ),
        ),
    )


def create_policy_context(
    processing_context: ProcessingContext,
    *,
    event: PolicyEvent,
) -> PolicyContext:
    pipeline = create_pipeline()

    return PolicyContext(
        processing_context=processing_context,
        pipeline=pipeline,
        stage=pipeline.stages[0],
        event=event,
    )


async def test_retry_allowed() -> None:
    context = create_context()

    context.set(
        ProcessingKeys.CURRENT_ATTEMPT,
        1,
    )

    context.set(
        ProcessingKeys.MAX_ATTEMPTS,
        3,
    )

    context.set(
        ProcessingKeys.EXCEPTION,
        RuntimeError("boom"),
    )

    policy = RetryPolicy()

    result = await policy.evaluate(
        create_policy_context(
            context,
            event=PolicyEvent.STAGE_FAILED,
        ),
    )

    assert result.continue_execution is True
    assert result.retry is True
    assert result.cancel_pipeline is False
    assert result.reason == "Retry allowed."


async def test_retry_not_allowed_when_attempts_are_exhausted() -> None:
    context = create_context()

    context.set(
        ProcessingKeys.CURRENT_ATTEMPT,
        3,
    )

    context.set(
        ProcessingKeys.MAX_ATTEMPTS,
        3,
    )

    context.set(
        ProcessingKeys.EXCEPTION,
        RuntimeError("boom"),
    )

    policy = RetryPolicy()

    result = await policy.evaluate(
        create_policy_context(
            context,
            event=PolicyEvent.STAGE_FAILED,
        ),
    )

    assert result.continue_execution is True
    assert result.retry is False
    assert result.cancel_pipeline is False
    assert result.reason == "Maximum retry attempts reached."


async def test_retry_is_ignored_without_exception() -> None:
    context = create_context()

    context.set(
        ProcessingKeys.CURRENT_ATTEMPT,
        1,
    )

    context.set(
        ProcessingKeys.MAX_ATTEMPTS,
        3,
    )

    policy = RetryPolicy()

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


async def test_retry_is_ignored_for_other_events() -> None:
    context = create_context()

    context.set(
        ProcessingKeys.CURRENT_ATTEMPT,
        1,
    )

    context.set(
        ProcessingKeys.MAX_ATTEMPTS,
        3,
    )

    context.set(
        ProcessingKeys.EXCEPTION,
        RuntimeError("boom"),
    )

    policy = RetryPolicy()

    result = await policy.evaluate(
        create_policy_context(
            context,
            event=PolicyEvent.BEFORE_STAGE,
        ),
    )

    assert result.continue_execution is True
    assert result.retry is False
    assert result.cancel_pipeline is False
    assert result.reason is None