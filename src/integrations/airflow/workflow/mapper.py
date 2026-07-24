from __future__ import annotations

from datetime import datetime
from typing import Any

from data_platform.workflow.models import (
    Workflow,
    WorkflowRun,
    WorkflowStatus,
)


class AirflowMapper:
    """
    Maps Airflow REST API models into platform workflow models.
    """

    _STATUS_MAPPING: dict[str, WorkflowStatus] = {
        "queued": WorkflowStatus.PENDING,
        "scheduled": WorkflowStatus.PENDING,
        "running": WorkflowStatus.RUNNING,
        "success": WorkflowStatus.SUCCESS,
        "failed": WorkflowStatus.FAILED,
        "up_for_retry": WorkflowStatus.RUNNING,
        "upstream_failed": WorkflowStatus.FAILED,
        "skipped": WorkflowStatus.SUCCESS,
        "removed": WorkflowStatus.CANCELLED,
    }

    @classmethod
    def to_workflow(
        cls,
        data: dict[str, Any],
    ) -> Workflow:
        return Workflow(
            identifier=data["dag_id"],
            name=data.get("dag_display_name") or data["dag_id"],
            description=data.get("description"),
            parameters={},
        )

    @classmethod
    def to_workflows(
        cls,
        payload: dict[str, Any],
    ) -> list[Workflow]:
        return [
            cls.to_workflow(item)
            for item in payload.get("dags", [])
        ]

    @classmethod
    def to_workflow_run(
        cls,
        workflow_id: str,
        workflow_name: str | None,
        data: dict[str, Any],
    ) -> WorkflowRun:
        return WorkflowRun(
            run_id=data["dag_run_id"],
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            status=cls._STATUS_MAPPING.get(
                data.get("state", "").lower(),
                WorkflowStatus.PENDING,
            ),
            queued_at=cls._parse_datetime(
                data.get("queued_at"),
            ),
            started_at=cls._parse_datetime(
                data.get("start_date"),
            ),
            finished_at=cls._parse_datetime(
                data.get("end_date"),
            ),
            parameters=data.get("conf", {}),
            metadata={
                "logical_date": data.get("logical_date"),
                "run_type": data.get("run_type"),
                "note": data.get("note"),
                "external_trigger": data.get("external_trigger"),
            },
        )

    @classmethod
    def to_workflow_runs(
        cls,
        workflow_id: str,
        workflow_name: str | None,
        payload: dict[str, Any],
    ) -> list[WorkflowRun]:
        return [
            cls.to_workflow_run(
                workflow_id=workflow_id,
                workflow_name=workflow_name,
                data=item,
            )
            for item in payload.get("dag_runs", [])
        ]

    @staticmethod
    def _parse_datetime(
        value: str | None,
    ) -> datetime | None:
        if value is None:
            return None

        return datetime.fromisoformat(
            value.replace("Z", "+00:00"),
        )