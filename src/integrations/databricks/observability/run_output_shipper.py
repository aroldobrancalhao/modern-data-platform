"""
Modern Data Platform

Ships the real output of a Databricks Job run's tasks to CloudWatch
Logs -- Sprint 13 close-out (the `databricks` log group,
module.cloudwatch_databricks, previously provisioned but unwired).

The 3 real Jobs this project runs (bronze, silver, full_pipeline --
infrastructure/databricks/*_job.yml) are all serverless notebook tasks
(no `new_cluster`/`existing_cluster` block, confirmed by reading the
bundle YAMLs directly). Databricks serverless compute has no
`cluster_log_conf` -- there is no driver/executor log to redirect
anywhere. The Jobs API's Get Run Output (`jobs.get_run_output`) is the
only log-shaped signal reachable at all for these tasks: each task's
notebook result (`NotebookOutput.result`), any top-level `logs`
(print-style output, separate from the notebook's own displayed
result), and `error`/`error_trace` on failure -- capped at 5MB by the
API itself (docs.databricks.com/api/workspace/jobs/getrunoutput), a
real, accepted limitation, not a bug this module works around.

`RunOutput.error` is populated even on a real success, by design
(its own docstring: "An error message indicating why a task failed OR
why output is not available" -- a notebook that completes without
calling `dbutils.notebook.exit()`, every notebook in this project's 4
real Jobs, has "no output available" in the API's own strict sense).
`_format_task_output` gates `error`/`error_trace` on the task's real
`result_state`, not the field's mere presence, so a successful task
never reads as failed.

Deliberately Airflow-agnostic, same principle as the rest of
src/integrations/databricks/ (DatabricksContext/
DatabricksComputeProvider don't import Airflow either): takes an
already-authenticated WorkspaceClient, not a Connection ID. The
caller (airflow/dags/marketplace_batch_pipeline.py) is responsible for
building that client from the `databricks_default` Connection -- not
DatabricksContext.workspace, which resolves ~/.databrickscfg's
`modern-data-platform` profile (expired, see
docs/environment-inventory.md, and the wrong auth mechanism for a
process running inside the Airflow container regardless).

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import logging

import watchtower
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import Run, RunOutput, RunResultState, RunTask


def ship_run_output_to_cloudwatch(
    *,
    workspace: WorkspaceClient,
    run_id: int,
    log_group_name: str,
) -> int:
    """
    Fetches the Job run's task list (`jobs.get_run`) and, for each task
    run, its output (`jobs.get_run_output`) -- ships one CloudWatch log
    event per task to `log_group_name`.

    Returns the number of task outputs shipped. Raises on a real
    Databricks API failure (including "this run has no tasks", which
    would otherwise silently ship zero events and look like success) --
    the caller decides whether that should fail its own task. Does
    NOT create the log group (`create_log_group=False`, same as
    data_platform.observability.logging_config's own CloudWatch
    handler) -- the group is Terraform-provisioned
    (module.cloudwatch_databricks) and this function's own IAM grant
    is deliberately scoped to only logs:CreateLogStream/PutLogEvents,
    not CreateLogGroup -- see
    infrastructure/terraform/environments/dev/security.tf.
    """
    run: Run = workspace.jobs.get_run(run_id=run_id)

    tasks: list[RunTask] = list(run.tasks or [])

    if not tasks:
        raise ValueError(f"Databricks run {run_id} has no task runs to ship.")

    logger = logging.getLogger(
        "integrations.databricks.observability.run_output_shipper"
    )
    logger.setLevel(logging.INFO)
    # Ship-only logger, same reasoning as every other CloudWatch
    # logger in this project (logging_config.py,
    # terraform_with_cloudwatch_logging.py) -- never hand records to
    # the root logger.
    logger.propagate = False

    handler = watchtower.CloudWatchLogHandler(
        log_group_name=log_group_name,
        create_log_group=False,
    )
    logger.addHandler(handler)

    shipped = 0

    try:
        for task in tasks:
            if task.run_id is None:
                continue

            output: RunOutput = workspace.jobs.get_run_output(run_id=task.run_id)

            logger.info(_format_task_output(run_id=run_id, task=task, output=output))

            shipped += 1
    finally:
        # Explicit close() blocks until the queue drains (watchtower's
        # own send_interval defaults to 60s) -- this is a short-lived
        # Airflow task, not a long-running process, so the events must
        # be flushed before it exits, not left for a batch window that
        # may never come.
        handler.close()

    return shipped


def _format_task_output(*, run_id: int, task: RunTask, output: RunOutput) -> str:
    """
    One line per task, plain text (not JSON -- there is no console
    pipeline this needs to stay consistent with, unlike
    data_platform.observability.logging_config's structlog-rendered
    lines). Includes whichever of notebook result / top-level logs /
    error the API actually returned for this task -- not every field
    is populated on every run (result_state absent while still
    running, logs absent unless the notebook printed something, error/
    error_trace absent on success).
    """
    state = task.state

    parts = [
        f"run_id={run_id}",
        f"task_key={task.task_key}",
        f"task_run_id={task.run_id}",
        f"life_cycle_state={state.life_cycle_state if state else None}",
        f"result_state={state.result_state if state else None}",
    ]

    if output.notebook_output is not None and output.notebook_output.result:
        result = output.notebook_output.result
        truncated = " (truncated)" if output.notebook_output.truncated else ""
        parts.append(f"notebook_result{truncated}={result}")

    if output.logs:
        truncated = " (truncated)" if output.logs_truncated else ""
        parts.append(f"logs{truncated}={output.logs}")

    # RunOutput.error's own docstring (databricks-sdk):
    # "An error message indicating why a task failed OR why output is
    # not available." -- confirmed real, documented API behavior, not
    # a bug: a notebook task that completes successfully without
    # calling dbutils.notebook.exit() (every notebook in this
    # project's 4 real Jobs) has "no output available" in the API's
    # own strict sense, and `error` gets populated with an explanatory
    # placeholder ("Please refer to the logs for this run on the
    # triggered run details page.") even though nothing failed.
    # Gating on the task's own result_state -- not the field's mere
    # presence -- is what actually distinguishes a real failure from
    # this benign case. Ambiguous state (state/result_state missing)
    # errs toward showing it rather than hiding a possible real error.
    task_succeeded = (
        state is not None and state.result_state == RunResultState.SUCCESS
    )

    if output.error and not task_succeeded:
        parts.append(f"error={output.error}")

    if output.error_trace and not task_succeeded:
        parts.append(f"error_trace={output.error_trace}")

    return " | ".join(parts)
