"""
Modern Data Platform
Processing Framework

Publishes WorkflowProvider results into the ProcessingContext.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.core.context_keys.workflow_keys import (
    WorkflowKeys,
)
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.workflow.models import WorkflowRun


class WorkflowContextWriter:
    """
    Translates a WorkflowRun into WorkflowKeys and publishes it into the
    ProcessingContext.

    This class knows about WorkflowRun (a provider-agnostic domain model)
    and about ProcessingContext/WorkflowKeys. It does not know about any
    concrete WorkflowProvider (Airflow, Prefect, Dagster, ...) -- the
    caller is responsible for obtaining the WorkflowRun from a Provider
    and passing it here.

    WorkflowKeys.WORKFLOW_ID, WORKFLOW_NAME and RUN_ID are always
    populated, since WorkflowRun always carries them.

    WorkflowKeys.EXECUTION_URL and SCHEDULE_ID are populated only when
    the Provider supplies "execution_url"/"schedule_id" inside
    WorkflowRun.metadata. As of this change, AirflowWorkflowMapper does
    not populate either key (it only fills "logical_date", "run_type",
    "note" and "external_trigger"), so these two ContextKeys will not be
    set for real Airflow runs until the mapper is extended -- that is a
    Provider/Mapper change, out of scope here.

    WorkflowKeys.TASK_ID and TASK_NAME are never written by this class:
    WorkflowRun represents a DAG-run-level execution, not an individual
    task instance, so there is no task-level data to publish at this
    level.
    """

    @staticmethod
    def write(
        run: WorkflowRun,
        context: ProcessingContext,
    ) -> None:
        """
        Publishes a WorkflowRun into the ProcessingContext.

        Parameters
        ----------
        run:
            The WorkflowRun returned by a WorkflowProvider (e.g. from
            ``provider.trigger(...)`` or ``provider.get_run(...)``).

        context:
            The ProcessingContext of the current execution.
        """

        context.set(
            WorkflowKeys.WORKFLOW_ID,
            run.workflow_id,
        )

        if run.workflow_name is not None:
            context.set(
                WorkflowKeys.WORKFLOW_NAME,
                run.workflow_name,
            )

        context.set(
            WorkflowKeys.RUN_ID,
            run.run_id,
        )

        execution_url = run.metadata.get("execution_url")

        if execution_url is not None:
            context.set(
                WorkflowKeys.EXECUTION_URL,
                execution_url,
            )

        schedule_id = run.metadata.get("schedule_id")

        if schedule_id is not None:
            context.set(
                WorkflowKeys.SCHEDULE_ID,
                schedule_id,
            )