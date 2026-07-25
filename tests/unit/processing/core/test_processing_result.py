"""
Modern Data Platform
Processing Framework

Unit tests for ProcessingResult.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.core.execution_metadata import ExecutionMetadata
from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.processing_result import ProcessingResult


def create_metadata() -> ExecutionMetadata:
    return ExecutionMetadata(
        execution_id="execution-1",
    )


def test_completed_result_succeeds() -> None:
    result = ProcessingResult(
        status=ExecutionStatus.COMPLETED,
        metadata=create_metadata(),
    )

    assert result.succeeded is True
    assert result.failed is False


def test_failed_result_fails() -> None:
    result = ProcessingResult(
        status=ExecutionStatus.FAILED,
        metadata=create_metadata(),
    )

    assert result.succeeded is False
    assert result.failed is True


def test_processing_result_preserves_error_information() -> None:
    result = ProcessingResult(
        status=ExecutionStatus.FAILED,
        metadata=create_metadata(),
        error_type="ValueError",
        error_message="Invalid value.",
    )

    assert result.error_type == "ValueError"
    assert result.error_message == "Invalid value."


def test_processing_result_without_error_information() -> None:
    result = ProcessingResult(
        status=ExecutionStatus.COMPLETED,
        metadata=create_metadata(),
    )

    assert result.error_type is None
    assert result.error_message is None