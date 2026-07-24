from __future__ import annotations

from data_platform.workflow import (
    Workflow,
    WorkflowProvider,
    WorkflowRun,
)

from ..core.airflow_client import AirflowClient
from .mapper import AirflowMapper


class AirflowWorkflowProvider(WorkflowProvider):

    def __init__(
        self,
        client: AirflowClient,
    ) -> None:

        self._client = client

    #
    # Workflows
    #

    def list_workflows(
        self,
    ) -> list[Workflow]:

        response = self._client.list_dags()

        return AirflowMapper.to_workflows(
            response.body,
        )

    def get_workflow(
        self,
        workflow_id: str,
    ) -> Workflow:

        response = self._client.get_dag(
            workflow_id,
        )

        return AirflowMapper.to_workflow(
            response.body,
        )

    #
    # Runs
    #

    def trigger(
        self,
        workflow_id: str,
        parameters: dict[str, object] | None = None,
    ) -> WorkflowRun:

        response = self._client.trigger_dag(
            workflow_id,
            parameters or {},
        )

        workflow = self.get_workflow(
            workflow_id,
        )

        return AirflowMapper.to_workflow_run(
            workflow_id=workflow.identifier,
            workflow_name=workflow.name,
            data=response.body,
        )

    def list_runs(
        self,
        workflow_id: str,
    ) -> list[WorkflowRun]:

        workflow = self.get_workflow(
            workflow_id,
        )

        response = self._client.list_dag_runs(
            workflow_id,
        )

        return AirflowMapper.to_workflow_runs(
            workflow_id=workflow.identifier,
            workflow_name=workflow.name,
            payload=response.body,
        )

    def get_run(
        self,
        workflow_id: str,
        run_id: str,
    ) -> WorkflowRun:

        workflow = self.get_workflow(
            workflow_id,
        )

        response = self._client.get_dag_run(
            workflow_id,
            run_id,
        )

        return AirflowMapper.to_workflow_run(
            workflow_id=workflow.identifier,
            workflow_name=workflow.name,
            data=response.body,
        )

    def cancel(
        self,
        workflow_id: str,
        run_id: str,
    ) -> None:

        self._client.cancel_dag_run(
            workflow_id,
            run_id,
        )