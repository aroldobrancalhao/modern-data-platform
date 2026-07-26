"""
Modern Data Platform
Processing Framework

Execution trace.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from data_platform.processing.core.execution_status import (
    ExecutionStatus,
)
from data_platform.processing.core.value_object import ValueObject
from data_platform.processing.tracing.trace_span import TraceSpan


@dataclass(frozen=True, slots=True)
class Trace(ValueObject):
    """
    Represents a pipeline execution trace.
    """

    execution_id: str

    pipeline_id: str

    pipeline_name: str

    status: ExecutionStatus

    started_at: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )

    finished_at: datetime | None = None

    duration: float | None = None

    exception: str | None = None

    spans: tuple[TraceSpan, ...] = field(
        default_factory=tuple,
    )