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
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import (
    StageResult,
)
from data_platform.processing.core.execution_status import (
    ExecutionStatus,
)
from data_platform.processing.events.hook_context import (
    HookContext,
)
from data_platform.processing.events.hook_type import (
    HookType,
)
from data_platform.processing.policies.failure_policy import (
    FailurePolicy,
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
            DummyStage(
                id="extract",
                name="Extract",
            ),
        ),
    )


async def test_should_continue_when_no_failure() -> None:

    policy = FailurePolicy()

    result = await policy.evaluate(
        HookContext(
            hook_type=HookType.AFTER_STAGE,
            pipeline=create_pipeline(),
            processing_context=create_context(),
        )
    )

    assert result.continue_execution is True
    assert result.cancel_pipeline is False


async def test_should_cancel_pipeline_when_fail_fast() -> None:

    policy = FailurePolicy()

    result = await policy.evaluate(
        HookContext(
            hook_type=HookType.STAGE_FAILED,
            pipeline=create_pipeline(),
            processing_context=create_context(),
            exception=RuntimeError(),
        )
    )

    assert result.continue_execution is False
    assert result.cancel_pipeline is True


async def test_should_continue_when_fail_fast_disabled() -> None:

    policy = FailurePolicy(
        fail_fast=False,
    )

    result = await policy.evaluate(
        HookContext(
            hook_type=HookType.STAGE_FAILED,
            pipeline=create_pipeline(),
            processing_context=create_context(),
            exception=RuntimeError(),
        )
    )

    assert result.continue_execution is True
    assert result.cancel_pipeline is False