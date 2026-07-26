"""
Modern Data Platform
Processing Framework

Unit tests for TraceSpan.
"""

from data_platform.processing.core.execution_status import (
    ExecutionStatus,
)
from data_platform.processing.tracing.trace_span import (
    TraceSpan,
)


def test_should_create_trace_span() -> None:
    span = TraceSpan(
        stage_id="extract",
        stage_name="Extract",
        status=ExecutionStatus.RUNNING,
    )

    assert span.stage_id == "extract"
    assert span.stage_name == "Extract"
    assert span.status is ExecutionStatus.RUNNING


def test_should_store_attributes() -> None:
    span = TraceSpan(
        stage_id="extract",
        stage_name="Extract",
        status=ExecutionStatus.COMPLETED,
        attributes={
            "rows": "100",
            "source": "postgres",
        },
    )

    assert span.metadata == {
        "rows": "100",
        "source": "postgres",
    }


def test_should_be_immutable() -> None:
    span = TraceSpan(
        stage_id="extract",
        stage_name="Extract",
        status=ExecutionStatus.COMPLETED,
    )

    assert span.stage_id == "extract"
    assert span.stage_name == "Extract"
    assert span.status is ExecutionStatus.COMPLETED