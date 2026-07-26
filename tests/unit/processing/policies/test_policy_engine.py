"""
Modern Data Platform
Processing Framework

Unit tests for PolicyEngine.
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
from data_platform.processing.policies.policy_engine import (
    PolicyEngine,
)
from data_platform.processing.policies.policy_manager import (
    PolicyManager,
)
from data_platform.processing.policies.policy_result import (
    PolicyResult,
)


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


class DummyPolicy(Policy):

    async def evaluate(
        self,
        context: PolicyContext,
    ) -> PolicyResult:

        return PolicyResult()


def create_stage() -> Stage:

    return DummyStage(
        id="stage-1",
        name="Dummy Stage",
    )


def create_context() -> PolicyContext:

    return PolicyContext(
        stage=create_stage(),
        processing_context=ProcessingContext(
            id="context-1",
            metadata=ExecutionMetadata(
                execution_id="execution-1",
            ),
        ),
    )


@pytest.mark.anyio
async def test_should_create_default_manager() -> None:

    engine = PolicyEngine()

    assert isinstance(
        engine.manager,
        PolicyManager,
    )


@pytest.mark.anyio
async def test_should_use_provided_manager() -> None:

    manager = PolicyManager()

    engine = PolicyEngine(
        manager=manager,
    )

    assert engine.manager is manager


@pytest.mark.anyio
async def test_should_evaluate_registered_policies() -> None:

    manager = PolicyManager(
        policies=[
            DummyPolicy(),
        ],
    )

    engine = PolicyEngine(
        manager=manager,
    )

    result = await engine.apply(
        create_context(),
    )

    assert isinstance(
        result,
        PolicyResult,
    )


@pytest.mark.anyio
async def test_should_return_default_result_when_empty() -> None:

    engine = PolicyEngine()

    result = await engine.apply(
        create_context(),
    )

    assert result == PolicyResult()