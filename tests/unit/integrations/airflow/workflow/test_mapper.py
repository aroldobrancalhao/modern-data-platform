from __future__ import annotations

from data_platform.workflow.models import WorkflowStatus

from integrations.airflow.workflow.mapper import AirflowMapper


def test_should_map_workflow() -> None:
    payload = {
        "dag_id": "daily_sales",
        "dag_display_name": "Daily Sales",
        "description": "Daily ETL",
    }

    workflow = AirflowMapper.to_workflow(payload)

    assert workflow.identifier == "daily_sales"
    assert workflow.name == "Daily Sales"
    assert workflow.description == "Daily ETL"


def test_should_map_workflow_without_display_name() -> None:
    payload = {
        "dag_id": "daily_sales",
        "description": None,
    }

    workflow = AirflowMapper.to_workflow(payload)

    assert workflow.identifier == "daily_sales"
    assert workflow.name == "daily_sales"


def test_should_map_workflow_run() -> None:
    payload = {
        "dag_run_id": "manual__001",
        "state": "success",
        "queued_at": "2026-07-18T10:00:00Z",
        "start_date": "2026-07-18T10:01:00Z",
        "end_date": "2026-07-18T10:02:00Z",
        "logical_date": "2026-07-18T10:00:00Z",
        "run_type": "manual",
        "external_trigger": True,
        "note": "integration test",
        "conf": {
            "country": "BR",
        },
    }

    run = AirflowMapper.to_workflow_run(
        workflow_id="daily_sales",
        workflow_name="Daily Sales",
        data=payload,
    )

    assert run.run_id == "manual__001"
    assert run.workflow_id == "daily_sales"
    assert run.workflow_name == "Daily Sales"

    assert run.status is WorkflowStatus.SUCCESS

    assert run.queued_at is not None
    assert run.started_at is not None
    assert run.finished_at is not None

    assert run.parameters["country"] == "BR"

    assert run.metadata["run_type"] == "manual"
    assert run.metadata["external_trigger"] is True


def test_should_map_workflow_runs() -> None:
    payload = {
        "dag_runs": [
            {
                "dag_run_id": "1",
                "state": "running",
                "conf": {},
            },
            {
                "dag_run_id": "2",
                "state": "success",
                "conf": {},
            },
        ],
    }

    runs = AirflowMapper.to_workflow_runs(
        workflow_id="daily_sales",
        workflow_name="Daily Sales",
        payload=payload,
    )

    assert len(runs) == 2

    assert runs[0].status is WorkflowStatus.RUNNING
    assert runs[1].status is WorkflowStatus.SUCCESS