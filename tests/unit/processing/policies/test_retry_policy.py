"""
Modern Data Platform
Processing Framework

Unit tests for RetryPolicy.
"""

from __future__ import annotations

import pytest

from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.core.execution_status import (
    ExecutionStatus,
)
from data_platform.processing.core.stage import (
    Stage,
)
from data_platform.processing.core.stage_result import (
    StageResult,
)
from data_platform.processing.policies.policy_context import (
    PolicyContext,
)
from data_platform.processing.policies.policy_result import (
    PolicyResult,
)
from data_platform.processing.policies.retry_policy import (
    RetryPolicy,
)

pytestmark = pytest.mark.anyio


class DummyStage(Stage):

    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:

        return StageResult(
            stage_id=self.id,
            stage_name=self.name,
            status=ExecutionStatus.COMPLETED,
            metadata=context.metadata,
        )


def create_stage() -> Stage:

    return DummyStage(
        id="stage",
        name="Stage",
    )


def create_context() -> ProcessingContext:

    return ProcessingContext(
        id="context",
        metadata=ExecutionMetadata(
            execution_id="execution",
        ),
    )


def create_policy_context() -> PolicyContext:

    return PolicyContext(
        stage=create_stage(),
        processing_context=create_context(),
    )


async def test_should_return_default_policy_result() -> None:

    policy = RetryPolicy()

    result = await policy.evaluate(
        create_policy_context(),
    )

    assert result == PolicyResult()


async def test_should_not_request_retry_by_default() -> None:

    policy = RetryPolicy()

    result = await policy.evaluate(
        create_policy_context(),
    )

    assert result.continue_execution is True
    assert result.retry is False
    assert result.cancel_pipeline is False
    assert result.reason is None