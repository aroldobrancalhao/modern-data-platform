"""
Modern Data Platform
Processing Framework

Unit tests for PolicyManager.
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
from data_platform.processing.policies.policy import (
    Policy,
)
from data_platform.processing.policies.policy_context import (
    PolicyContext,
)
from data_platform.processing.policies.policy_manager import (
    PolicyManager,
)
from data_platform.processing.policies.policy_result import (
    PolicyResult,
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


class ContinuePolicy(Policy):

    async def evaluate(
        self,
        context: PolicyContext,
    ) -> PolicyResult:

        return PolicyResult()


class RetryPolicyStub(Policy):

    async def evaluate(
        self,
        context: PolicyContext,
    ) -> PolicyResult:

        return PolicyResult(
            retry=True,
        )


class CancelPolicy(Policy):

    async def evaluate(
        self,
        context: PolicyContext,
    ) -> PolicyResult:

        return PolicyResult(
            continue_execution=False,
            cancel_pipeline=True,
            reason="Cancelled",
        )


def policy_context() -> PolicyContext:

    return PolicyContext(
        stage=create_stage(),
        processing_context=create_context(),
    )


async def test_should_return_default_result_when_no_policies() -> None:

    manager = PolicyManager()

    result = await manager.evaluate(
        policy_context(),
    )

    assert result.continue_execution is True
    assert result.retry is False
    assert result.cancel_pipeline is False
    assert result.reason is None


async def test_should_merge_retry_results() -> None:

    manager = PolicyManager(
        (
            ContinuePolicy(),
            RetryPolicyStub(),
        ),
    )

    result = await manager.evaluate(
        policy_context(),
    )

    assert result.continue_execution is True
    assert result.retry is True
    assert result.cancel_pipeline is False


async def test_should_stop_when_policy_cancels_pipeline() -> None:

    manager = PolicyManager(
        (
            ContinuePolicy(),
            CancelPolicy(),
        ),
    )

    result = await manager.evaluate(
        policy_context(),
    )

    assert result.continue_execution is False
    assert result.cancel_pipeline is True
    assert result.reason == "Cancelled"


async def test_should_expose_registered_policies() -> None:

    manager = PolicyManager(
        (
            ContinuePolicy(),
            RetryPolicyStub(),
        ),
    )

    assert len(manager.policies) == 2