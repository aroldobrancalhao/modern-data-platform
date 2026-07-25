"""
Modern Data Platform
Processing Framework

Log entry.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime

from data_platform.processing.core.value_object import ValueObject
from data_platform.processing.logging.log_level import LogLevel


@dataclass(
    frozen=True,
    eq=False,
    slots=True,
)
class LogEntry(ValueObject):
    """
    Immutable log entry.
    """

    level: LogLevel

    message: str

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )

    execution_id: str | None = None

    pipeline_id: str | None = None

    pipeline_name: str | None = None

    stage_id: str | None = None

    stage_name: str | None = None

    duration: float | None = None

    exception: Exception | None = None

    extra: tuple[tuple[str, str], ...] = field(
        default_factory=tuple,
    )

    def __init__(
        self,
        *,
        level: LogLevel,
        message: str,
        timestamp: datetime | None = None,
        execution_id: str | None = None,
        pipeline_id: str | None = None,
        pipeline_name: str | None = None,
        stage_id: str | None = None,
        stage_name: str | None = None,
        duration: float | None = None,
        exception: Exception | None = None,
        extra: Mapping[str, str] | None = None,
    ) -> None:
        object.__setattr__(self, "level", level)
        object.__setattr__(self, "message", message)
        object.__setattr__(
            self,
            "timestamp",
            timestamp or datetime.now(UTC),
        )
        object.__setattr__(
            self,
            "execution_id",
            execution_id,
        )
        object.__setattr__(
            self,
            "pipeline_id",
            pipeline_id,
        )
        object.__setattr__(
            self,
            "pipeline_name",
            pipeline_name,
        )
        object.__setattr__(
            self,
            "stage_id",
            stage_id,
        )
        object.__setattr__(
            self,
            "stage_name",
            stage_name,
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

        normalized = tuple(
            sorted((extra or {}).items())
        )

        object.__setattr__(
            self,
            "extra",
            normalized,
        )

    @property
    def metadata(
        self,
    ) -> Mapping[str, str]:
        return dict(self.extra)