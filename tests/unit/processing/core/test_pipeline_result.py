"""
Modern Data Platform
Processing Framework

Unit tests for PipelineResult.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.core.execution_metadata import ExecutionMetadata
from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.pipeline_result import PipelineResult
from data_platform.processing.core.stage_result import StageResult


def metadata() -> ExecutionMetadata:
    return ExecutionMetadata(
        execution_id="execution-1",
    )


def stage(
    name: str,
    status: ExecutionStatus,
) -> StageResult:
    return StageResult(
        status=status,
        metadata=metadata(),
        stage_id=name.lower(),
        stage_name=name,
    )


def test_empty_pipeline_result() -> None:
    result = PipelineResult(
        status=ExecutionStatus.COMPLETED,
        metadata=metadata(),
    )

    assert result.total_stages == 0
    assert result.successful_stages == 0
    assert result.failed_stages == 0
    assert result.last_result is None
    assert result.has_failures is False


def test_pipeline_result_counts_stage_results() -> None:
    result = PipelineResult(
        status=ExecutionStatus.COMPLETED,
        metadata=metadata(),
        stage_results=(
            stage("Extract", ExecutionStatus.COMPLETED),
            stage("Transform", ExecutionStatus.COMPLETED),
            stage("Load", ExecutionStatus.FAILED),
        ),
    )

    assert result.total_stages == 3
    assert result.successful_stages == 2
    assert result.failed_stages == 1
    assert result.has_failures is True


def test_pipeline_result_returns_last_stage() -> None:
    last = stage(
        "Load",
        ExecutionStatus.COMPLETED,
    )

    result = PipelineResult(
        status=ExecutionStatus.COMPLETED,
        metadata=metadata(),
        stage_results=(
            stage("Extract", ExecutionStatus.COMPLETED),
            last,
        ),
    )

    assert result.last_result is last


def test_pipeline_result_inherits_processing_result_behavior() -> None:
    result = PipelineResult(
        status=ExecutionStatus.FAILED,
        metadata=metadata(),
    )

    assert result.failed is True
    assert result.succeeded is False