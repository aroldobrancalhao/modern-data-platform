class WorkflowError(Exception):
    """
    Base exception for workflow operations.
    """


class WorkflowNotFoundError(WorkflowError):
    """
    Raised when a workflow cannot be found.
    """


class WorkflowExecutionError(WorkflowError):
    """
    Raised when a workflow execution fails.
    """