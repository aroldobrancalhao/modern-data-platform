"""
Modern Data Platform
Processing Framework

Trace span.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

from data_platform.processing.core.value_object import ValueObject
from data_platform.processing.core.execution_status import ExecutionStatus


@dataclass(frozen=True, slots=True)
class TraceSpan(ValueObject):
    """
    Represents a traced pipeline stage execution.
    """

    stage_id: str
    stage_name: str

    status: ExecutionStatus

    started_at: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )

    finished_at: datetime | None = None

    duration: float | None = None

    exception: str | None = None

    attributes: tuple[tuple[str, str], ...] = field(
        default_factory=tuple,
    )

    def __init__(
        self,
        *,
        stage_id: str,
        stage_name: str,
        status: ExecutionStatus,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        duration: float | None = None,
        exception: str | None = None,
        attributes: Mapping[str, str] | None = None,
    ) -> None:
        object.__setattr__(self, "stage_id", stage_id)
        object.__setattr__(self, "stage_name", stage_name)
        object.__setattr__(self, "status", status)

        object.__setattr__(
            self,
            "started_at",
            started_at or datetime.now(UTC),
        )

        object.__setattr__(
            self,
            "finished_at",
            finished_at,
        )

        object.__setattr__(
            self,
            "duration",
            duration,
        )

        object.__setattr__(
            self,
            "exception",
            exception,
        )

        object.__setattr__(
            self,
            "attributes",
            tuple(sorted((attributes or {}).items())),
        )

    @property
    def metadata(self) -> dict[str, str]:
        return dict(self.attributes)