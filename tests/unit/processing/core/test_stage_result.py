"""
Modern Data Platform
Processing Framework

Unit tests for StageResult.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.core.execution_metadata import ExecutionMetadata
from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.stage_result import StageResult


def create_metadata() -> ExecutionMetadata:
    return ExecutionMetadata(
        execution_id="execution-1",
    )


def test_stage_result_defaults_attempt_to_one() -> None:
    result = StageResult(
        status=ExecutionStatus.COMPLETED,
        metadata=create_metadata(),
        stage_id="stage-1",
        stage_name="Extract",
    )

    assert result.attempt == 1


def test_stage_result_accepts_custom_attempt() -> None:
    result = StageResult(
        status=ExecutionStatus.COMPLETED,
        metadata=create_metadata(),
        stage_id="stage-1",
        stage_name="Extract",
        attempt=3,
    )

    assert result.attempt == 3


def test_stage_result_preserves_stage_information() -> None:
    result = StageResult(
        status=ExecutionStatus.COMPLETED,
        metadata=create_metadata(),
        stage_id="extract",
        stage_name="Extract Customers",
    )

    assert result.stage_id == "extract"
    assert result.stage_name == "Extract Customers"


def test_stage_result_inherits_processing_result_behavior() -> None:
    result = StageResult(
        status=ExecutionStatus.FAILED,
        metadata=create_metadata(),
        stage_id="stage-1",
        stage_name="Extract",
    )

    assert result.failed is True
    assert result.succeeded is False