"""
Modern Data Platform
Processing Framework

Unit tests for ConsoleTracer.
"""

from data_platform.processing.core.execution_status import (
    ExecutionStatus,
)
from data_platform.processing.tracing.console_tracer import (
    ConsoleTracer,
)
from data_platform.processing.tracing.trace import Trace


def test_should_create_console_tracer() -> None:
    tracer = ConsoleTracer()

    assert tracer is not None


def test_should_record_trace() -> None:
    tracer = ConsoleTracer()

    trace = Trace(
        execution_id="execution",
        pipeline_id="pipeline",
        pipeline_name="Pipeline",
        status=ExecutionStatus.COMPLETED,
    )

    tracer.record(trace)