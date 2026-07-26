"""
Modern Data Platform
Processing Framework

Unit tests for TimeoutPolicy.
"""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta

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
from data_platform.processing.policies.policy_context import (
    PolicyContext,
)
from data_platform.processing.policies.timeout_policy import (
    TimeoutPolicy,
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


def create_context(
    *,
    started_at: datetime | None,
) -> ProcessingContext:

    return ProcessingContext(
        id="context",
        metadata=ExecutionMetadata(
            execution_id="execution",
            started_at=started_at,
        ),
    )


async def test_should_continue_when_started_at_is_none() -> None:

    policy = TimeoutPolicy(timeout=10)

    result = await policy.evaluate(
        PolicyContext(
            stage=create_stage(),
            processing_context=create_context(
                started_at=None,
            ),
        ),
    )

    assert result.continue_execution is True
    assert result.cancel_pipeline is False


async def test_should_continue_before_timeout() -> None:

    policy = TimeoutPolicy(timeout=60)

    result = await policy.evaluate(
        PolicyContext(
            stage=create_stage(),
            processing_context=create_context(
                started_at=datetime.now(
                    UTC,
                )
                - timedelta(
                    seconds=5,
                ),
            ),
        ),
    )

    assert result.continue_execution is True
    assert result.cancel_pipeline is False


async def test_should_cancel_after_timeout() -> None:

    policy = TimeoutPolicy(timeout=5)

    result = await policy.evaluate(
        PolicyContext(
            stage=create_stage(),
            processing_context=create_context(
                started_at=datetime.now(
                    UTC,
                )
                - timedelta(
                    seconds=30,
                ),
            ),
        ),
    )

    assert result.continue_execution is False
    assert result.cancel_pipeline is True
    assert result.reason == "Execution timeout exceeded."