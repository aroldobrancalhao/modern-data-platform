from databricks.sdk.service.jobs import Run

from data_platform.models.compute import Workload
from integrations.databricks.core.databricks_context import DatabricksContext


class DatabricksClient:
    """
    Client responsible for executing existing Databricks Jobs.
    """

    def __init__(self, context: DatabricksContext) -> None:
        self._context = context

    def run(self, workload: Workload) -> Run:
        job_id = self._context.resolve_job(workload.identifier)

        waiter = self._context.workspace.jobs.run_now(
            job_id=job_id,
            job_parameters=dict(workload.parameters),
        )

        completed_run = waiter.result()

        if completed_run.run_id is None:
            raise RuntimeError(
                "Databricks returned a completed run without a run_id."
            )

        return self._context.workspace.jobs.get_run(
            run_id=completed_run.run_id,
        )