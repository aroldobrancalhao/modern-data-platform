from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .workflow_status import WorkflowStatus


@dataclass(frozen=True, slots=True)
class WorkflowRun:
    """
    Represents a workflow execution.
    """

    run_id: str

    workflow_id: str

    workflow_name: str | None

    status: WorkflowStatus

    queued_at: datetime | None = None

    started_at: datetime | None = None

    finished_at: datetime | None = None

    parameters: dict[str, Any] = field(default_factory=dict)

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        """
        Backward-compatible alias for run_id.
        """
        return self.run_id