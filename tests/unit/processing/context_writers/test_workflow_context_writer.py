"""
Modern Data Platform
Processing Framework

Unit tests for WorkflowContextWriter.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.context_writers.workflow_context_writer import (
    WorkflowContextWriter,
)
from data_platform.processing.core.context_keys.workflow_keys import (
    WorkflowKeys,
)
from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.workflow.models import WorkflowRun, WorkflowStatus


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-1",
        metadata=ExecutionMetadata(execution_id="execution-1"),
    )


def test_write_populates_workflow_id_run_id_and_name() -> None:
    context = create_context()

    run = WorkflowRun(
        run_id="run-1",
        workflow_id="dag-1",
        workflow_name="Dag 1",
        status=WorkflowStatus.SUCCESS,
    )

    WorkflowContextWriter.write(run, context)

    assert context.get(WorkflowKeys.WORKFLOW_ID) == "dag-1"
    assert context.get(WorkflowKeys.WORKFLOW_NAME) == "Dag 1"
    assert context.get(WorkflowKeys.RUN_ID) == "run-1"


def test_write_omits_workflow_name_when_none() -> None:
    context = create_context()

    run = WorkflowRun(
        run_id="run-1",
        workflow_id="dag-1",
        workflow_name=None,
        status=WorkflowStatus.SUCCESS,
    )

    WorkflowContextWriter.write(run, context)

    assert context.contains(WorkflowKeys.WORKFLOW_NAME) is False


def test_write_populates_execution_url_and_schedule_id_when_present() -> None:
    context = create_context()

    run = WorkflowRun(
        run_id="run-1",
        workflow_id="dag-1",
        workflow_name="Dag 1",
        status=WorkflowStatus.SUCCESS,
        metadata={
            "execution_url": "https://airflow.example.com/runs/run-1",
            "schedule_id": "schedule-1",
        },
    )

    WorkflowContextWriter.write(run, context)

    assert (
        context.get(WorkflowKeys.EXECUTION_URL)
        == "https://airflow.example.com/runs/run-1"
    )
    assert context.get(WorkflowKeys.SCHEDULE_ID) == "schedule-1"


def test_write_omits_execution_url_and_schedule_id_when_absent() -> None:
    context = create_context()

    run = WorkflowRun(
        run_id="run-1",
        workflow_id="dag-1",
        workflow_name="Dag 1",
        status=WorkflowStatus.SUCCESS,
    )

    WorkflowContextWriter.write(run, context)

    assert context.contains(WorkflowKeys.EXECUTION_URL) is False
    assert context.contains(WorkflowKeys.SCHEDULE_ID) is False


def test_write_never_sets_task_keys() -> None:
    context = create_context()

    run = WorkflowRun(
        run_id="run-1",
        workflow_id="dag-1",
        workflow_name="Dag 1",
        status=WorkflowStatus.SUCCESS,
    )

    WorkflowContextWriter.write(run, context)

    assert context.contains(WorkflowKeys.TASK_ID) is False
    assert context.contains(WorkflowKeys.TASK_NAME) is False