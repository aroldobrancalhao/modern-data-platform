"""
Modern Data Platform
Processing Framework

Execution metadata.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping

from data_platform.processing.core.value_object import ValueObject


@dataclass(frozen=True, slots=True)
class ExecutionMetadata(ValueObject):
    """
    Immutable metadata describing a processing execution.

    This object contains contextual information used for
    tracing, correlation and observability.

    It intentionally does not contain execution results,
    metrics or business data.
    """

    execution_id: str

    pipeline_id: str | None = None

    stage_id: str | None = None

    correlation_id: str | None = None

    parent_execution_id: str | None = None

    started_at: datetime | None = None

    attributes: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )

    def with_attribute(
        self,
        key: str,
        value: Any,
    ) -> "ExecutionMetadata":
        """
        Returns a new instance with an additional attribute.
        """

        updated = dict(self.attributes)
        updated[key] = value

        return ExecutionMetadata(
            execution_id=self.execution_id,
            pipeline_id=self.pipeline_id,
            stage_id=self.stage_id,
            correlation_id=self.correlation_id,
            parent_execution_id=self.parent_execution_id,
            started_at=self.started_at,
            attributes=MappingProxyType(updated),
        )