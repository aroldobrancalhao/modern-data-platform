from __future__ import annotations

from databricks.sdk.errors import DatabricksError
from databricks.sdk.service.jobs import Run

from data_platform.models.compute import Workload

from .databricks_context import DatabricksContext
from .databricks_exception_mapper import DatabricksExceptionMapper


class DatabricksClient:
    """
    Client responsible for executing existing Databricks Jobs.
    """

    def __init__(self, context: DatabricksContext) -> None:
        self._context = context

    def run(self, workload: Workload) -> Run:

        try:
            job_id = self._context.resolve_job(workload.identifier)

            waiter = self._context.workspace.jobs.run_now(
                job_id=job_id,
                job_parameters=dict(workload.parameters),
            )

            completed_run = waiter.result()

        except DatabricksError as exception:
            raise DatabricksExceptionMapper.translate(
                exception,
            ) from exception

        if completed_run.run_id is None:
            raise RuntimeError(
                "Databricks returned a completed run without a run_id."
            )

        try:
            return self._context.workspace.jobs.get_run(
                run_id=completed_run.run_id,
            )

        except DatabricksError as exception:
            raise DatabricksExceptionMapper.translate(
                exception,
            ) from exception