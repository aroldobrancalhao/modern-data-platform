from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from data_platform.workflow.models.workflow_status import WorkflowStatus


@dataclass(frozen=True, slots=True)
class WorkflowRun:
    """
    Represents a workflow execution.

    This model is provider-agnostic and contains only execution
    metadata exposed by the platform.

    Concrete providers are responsible for mapping their native
    execution models into this abstraction.
    """

    run_id: str
    workflow_id: str
    workflow_name: str | None
    status: WorkflowStatus

    started_at: datetime | None = None
    finished_at: datetime | None = None

    parameters: dict[str, Any] = field(default_factory=dict)