"""
Modern Data Platform
Processing Framework

Unit tests for Trace.
"""

from data_platform.processing.core.execution_status import (
    ExecutionStatus,
)
from data_platform.processing.tracing.trace import Trace
from data_platform.processing.tracing.trace_span import (
    TraceSpan,
)


def test_should_create_trace() -> None:
    trace = Trace(
        execution_id="execution",
        pipeline_id="pipeline",
        pipeline_name="Pipeline",
        status=ExecutionStatus.RUNNING,
    )

    assert trace.execution_id == "execution"
    assert trace.pipeline_id == "pipeline"
    assert trace.pipeline_name == "Pipeline"
    assert trace.status is ExecutionStatus.RUNNING


def test_should_store_spans() -> None:
    span = TraceSpan(
        stage_id="extract",
        stage_name="Extract",
        status=ExecutionStatus.COMPLETED,
    )

    trace = Trace(
        execution_id="execution",
        pipeline_id="pipeline",
        pipeline_name="Pipeline",
        status=ExecutionStatus.COMPLETED,
        spans=(span,),
    )

    assert len(trace.spans) == 1
    assert trace.spans[0] == span


def test_should_be_immutable() -> None:
    trace = Trace(
        execution_id="execution",
        pipeline_id="pipeline",
        pipeline_name="Pipeline",
        status=ExecutionStatus.COMPLETED,
    )

    assert trace.execution_id == "execution"
    assert trace.status is ExecutionStatus.COMPLETED