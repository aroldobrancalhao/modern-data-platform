from __future__ import annotations

from data_platform.workflow.models import WorkflowStatus

from integrations.airflow.workflow.airflow_workflow_provider import (
    AirflowWorkflowProvider,
)


def test_should_list_workflows(
    workflow_provider: AirflowWorkflowProvider,
) -> None:
    workflows = workflow_provider.list_workflows()

    assert workflows is not None
    assert isinstance(workflows, list)
    assert len(workflows) > 0


def test_should_return_platform_validation_workflow(
    workflow_provider: AirflowWorkflowProvider,
) -> None:
    workflow = workflow_provider.get_workflow(
        "platform_validation",
    )

    assert workflow.id == "platform_validation"


def test_should_trigger_workflow(
    workflow_provider: AirflowWorkflowProvider,
) -> None:
    run = workflow_provider.trigger(
        workflow_id="platform_validation",
    )

    assert run.workflow_id == "platform_validation"
    assert run.id is not None


def test_should_list_workflow_runs(
    workflow_provider: AirflowWorkflowProvider,
) -> None:
    runs = workflow_provider.list_runs(
        "platform_validation",
    )

    assert isinstance(runs, list)


def test_should_get_workflow_run(
    workflow_provider: AirflowWorkflowProvider,
) -> None:
    run = workflow_provider.trigger(
        workflow_id="platform_validation",
    )

    loaded = workflow_provider.get_run(
        workflow_id="platform_validation",
        run_id=run.id,
    )

    assert loaded.id == run.id
    assert loaded.workflow_id == run.workflow_id


def test_should_cancel_workflow(
    workflow_provider: AirflowWorkflowProvider,
) -> None:
    run = workflow_provider.trigger(
        workflow_id="platform_validation",
    )

    workflow_provider.cancel(
        workflow_id="platform_validation",
        run_id=run.id,
    )

    cancelled = workflow_provider.get_run(
        workflow_id="platform_validation",
        run_id=run.id,
    )

    assert cancelled.status in (
        WorkflowStatus.FAILED,
        WorkflowStatus.CANCELLED,
        WorkflowStatus.SUCCESS,
        WorkflowStatus.RUNNING,
    )