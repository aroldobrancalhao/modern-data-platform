"""
Modern Data Platform
Processing Framework

Unit tests for ComputeContextWriter.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.models.compute import Execution, ExecutionStatus, Workload
from data_platform.processing.context_writers.compute_context_writer import (
    ComputeContextWriter,
)
from data_platform.processing.core.context_keys.compute_keys import (
    ComputeKeys,
)
from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-1",
        metadata=ExecutionMetadata(execution_id="execution-1"),
    )


def test_write_populates_job_id_and_run_id() -> None:
    context = create_context()

    workload = Workload(identifier="job-123")

    execution = Execution(
        execution_id="run-456",
        status=ExecutionStatus.RUNNING,
    )

    ComputeContextWriter.write(workload, execution, context)

    assert context.get(ComputeKeys.JOB_ID) == "job-123"
    assert context.get(ComputeKeys.RUN_ID) == "run-456"


def test_write_does_not_set_fields_absent_from_the_domain_model() -> None:
    context = create_context()

    workload = Workload(identifier="job-123")

    execution = Execution(
        execution_id="run-456",
        status=ExecutionStatus.SUCCEEDED,
    )

    ComputeContextWriter.write(workload, execution, context)

    assert context.contains(ComputeKeys.JOB_NAME) is False
    assert context.contains(ComputeKeys.SESSION_ID) is False
    assert context.contains(ComputeKeys.APPLICATION_ID) is False
    assert context.contains(ComputeKeys.CLUSTER_ID) is False