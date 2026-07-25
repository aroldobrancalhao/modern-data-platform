"""
Modern Data Platform
Processing Framework

Unit tests for Stage.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.core.execution_metadata import ExecutionMetadata
from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.processing_context import ProcessingContext
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult

import pytest

pytestmark = pytest.mark.anyio

class DummyStage(Stage):
    """
    Concrete Stage implementation used for tests.
    """

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
        id="context-1",
        metadata=ExecutionMetadata(
            execution_id="execution-1",
        ),
    )


def test_stage_preserves_identifier() -> None:
    stage = DummyStage(
        id="extract",
        name="Extract",
    )

    assert stage.id == "extract"


def test_stage_preserves_name() -> None:
    stage = DummyStage(
        id="extract",
        name="Extract Customers",
    )

    assert stage.name == "Extract Customers"


async def test_execute_returns_stage_result() -> None:
    context = create_context()

    stage = DummyStage(
        id="extract",
        name="Extract",
    )

    result = await stage.execute(context)

    assert isinstance(result, StageResult)


async def test_execute_returns_completed_status() -> None:
    context = create_context()

    stage = DummyStage(
        id="extract",
        name="Extract",
    )

    result = await stage.execute(context)

    assert result.status == ExecutionStatus.COMPLETED


async def test_execute_preserves_metadata() -> None:
    context = create_context()

    stage = DummyStage(
        id="extract",
        name="Extract",
    )

    result = await stage.execute(context)

    assert result.metadata is context.metadata


async def test_execute_preserves_stage_id() -> None:
    context = create_context()

    stage = DummyStage(
        id="customer_extract",
        name="Extract",
    )

    result = await stage.execute(context)

    assert result.stage_id == "customer_extract"


async def test_execute_preserves_stage_name() -> None:
    context = create_context()

    stage = DummyStage(
        id="extract",
        name="Extract Customers",
    )

    result = await stage.execute(context)

    assert result.stage_name == "Extract Customers"


async def test_execute_result_succeeds() -> None:
    context = create_context()

    stage = DummyStage(
        id="extract",
        name="Extract",
    )

    result = await stage.execute(context)

    assert result.succeeded is True
    assert result.failed is False


async def test_multiple_executions_return_new_results() -> None:
    context = create_context()

    stage = DummyStage(
        id="extract",
        name="Extract",
    )

    result1 = await stage.execute(context)
    result2 = await stage.execute(context)

    assert result1 is not result2