from enum import StrEnum, unique


@unique
class WorkflowKeys(StrEnum):
    """Keys produced by workflow providers."""

    WORKFLOW_ID = "workflow.workflow_id"
    WORKFLOW_NAME = "workflow.workflow_name"

    RUN_ID = "workflow.run_id"

    TASK_ID = "workflow.task_id"
    TASK_NAME = "workflow.task_name"

    EXECUTION_URL = "workflow.execution_url"

    SCHEDULE_ID = "workflow.schedule_id"