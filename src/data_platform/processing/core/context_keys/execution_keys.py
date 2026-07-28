from enum import StrEnum, unique


@unique
class ExecutionKeys(StrEnum):
    """Keys that describe the execution lifecycle."""

    EXECUTION_ID = "execution.execution_id"
    PARENT_EXECUTION_ID = "execution.parent_execution_id"
    CORRELATION_ID = "execution.correlation_id"

    STATUS = "execution.status"

    START_TIME = "execution.start_time"
    END_TIME = "execution.end_time"
    DURATION = "execution.duration"