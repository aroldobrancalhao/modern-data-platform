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


def test_stage_result_output_defaults_to_an_empty_dict() -> None:
    result = StageResult(
        status=ExecutionStatus.COMPLETED,
        metadata=create_metadata(),
        stage_id="stage-1",
        stage_name="Extract",
    )

    assert result.output == {}


def test_stage_result_output_carries_arbitrary_structured_data() -> None:
    """
    output is what a Stage returns instead of publishing into the
    shared ProcessingContext via a ContextWriter -- see
    PostgresExtractionStage, and ParallelExecutor's docstring for why
    that distinction matters for a Stage that might run inside a
    parallel group.
    """

    result = StageResult(
        status=ExecutionStatus.COMPLETED,
        metadata=create_metadata(),
        stage_id="extract-customers",
        stage_name="Extract Customers",
        output={
            "uri": "s3://bucket/raw/customers/abc.parquet",
            "bucket": "bucket",
            "object_key": "raw/customers/abc.parquet",
        },
    )

    assert result.output["uri"] == "s3://bucket/raw/customers/abc.parquet"
    assert result.output["bucket"] == "bucket"
    assert result.output["object_key"] == "raw/customers/abc.parquet"


def test_stage_result_output_instances_do_not_share_state() -> None:
    """
    Guards against the classic mutable-default-argument bug -- two
    StageResults with no explicit output must not accidentally share
    the same dict.
    """

    first = StageResult(
        status=ExecutionStatus.COMPLETED,
        metadata=create_metadata(),
        stage_id="a",
        stage_name="A",
    )

    second = StageResult(
        status=ExecutionStatus.COMPLETED,
        metadata=create_metadata(),
        stage_id="b",
        stage_name="B",
    )

    first.output["leaked"] = True

    assert second.output == {}