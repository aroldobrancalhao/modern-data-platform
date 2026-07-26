"""
Modern Data Platform
Processing Framework

Unit tests for FailurePolicy.
"""

from __future__ import annotations

import pytest

from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.execution_status import (
    ExecutionStatus,
)
from data_platform.processing.core.processing_context import (
    ProcessingContext,
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

pytestmark = pytest.mark.anyio


class DummyStage(Stage):

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


async def test_should_continue_when_no_failure() -> None:

    policy = FailurePolicy()

    result = await policy.evaluate(
        PolicyContext(
            stage=create_stage(),
            processing_context=create_context(),
        ),
    )

    assert result.continue_execution is True
    assert result.cancel_pipeline is False
    assert result.reason is None


async def test_should_cancel_pipeline_when_failure() -> None:

    policy = FailurePolicy()

    context = create_context()
    context.set(
        "exception",
        RuntimeError(),
    )

    result = await policy.evaluate(
        PolicyContext(
            stage=create_stage(),
            processing_context=context,
        ),
    )

    assert result.continue_execution is False
    assert result.cancel_pipeline is True
    assert (
        result.reason
        == "Pipeline interrupted due to failure."
    )


async def test_should_continue_when_fail_fast_disabled() -> None:

    policy = FailurePolicy(
        fail_fast=False,
    )

    context = create_context()
    context.set(
        "exception",
        RuntimeError(),
    )

    result = await policy.evaluate(
        PolicyContext(
            stage=create_stage(),
            processing_context=context,
        ),
    )

    assert result.continue_execution is True
    assert result.cancel_pipeline is False
    assert (
        result.reason
        == "Failure ignored by policy."
    )