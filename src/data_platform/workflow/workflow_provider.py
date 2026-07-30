from abc import abstractmethod

from data_platform.contracts.base_provider import BaseProvider
from data_platform.workflow.models import Workflow
from data_platform.workflow.models import WorkflowRun


class WorkflowProvider(BaseProvider):
    """
    Contract implemented by workflow orchestration providers.

    A WorkflowProvider is responsible for interacting with workflow
    orchestration engines (Airflow, Prefect, Dagster, etc.) while
    exposing a provider-agnostic API.
    """

    @abstractmethod
    def list_workflows(
        self,
    ) -> list[Workflow]:
        """
        Returns all available workflows.
        """
        raise NotImplementedError

    @abstractmethod
    def get_workflow(
        self,
        workflow_id: str,
    ) -> Workflow:
        """
        Returns a workflow by its identifier.
        """
        raise NotImplementedError

    @abstractmethod
    def trigger(
        self,
        workflow_id: str,
        parameters: dict[str, object] | None = None,
    ) -> WorkflowRun:
        """
        Starts a workflow execution.
        """
        raise NotImplementedError

    @abstractmethod
    def get_run(
        self,
        workflow_id: str,
        run_id: str,
    ) -> WorkflowRun:
        """
        Returns information about a workflow execution.
        """
        raise NotImplementedError

    @abstractmethod
    def list_runs(
        self,
        workflow_id: str,
    ) -> list[WorkflowRun]:
        """
        Returns all executions for a workflow.
        """
        raise NotImplementedError

    @abstractmethod
    def cancel(
        self,
        workflow_id: str,
        run_id: str,
    ) -> None:
        """
        Cancels a running workflow execution.
        """
        raise NotImplementedError