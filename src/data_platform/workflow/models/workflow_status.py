from enum import StrEnum


class WorkflowStatus(StrEnum):
    """
    Represents the lifecycle status of a workflow execution.

    These values are platform-level statuses and must remain
    independent of any orchestration engine implementation.
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"