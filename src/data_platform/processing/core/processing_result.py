"""
Modern Data Platform
Processing Framework

Base processing result.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass

from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.execution_status import (
    ExecutionStatus,
)
from data_platform.processing.core.value_object import ValueObject


@dataclass(
    frozen=True,
    eq=False,
    slots=True,
)
class ProcessingResult(ValueObject):
    """
    Base result for processing executions.
    """

    status: ExecutionStatus

    metadata: ExecutionMetadata

    error_type: str | None = None

    error_message: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status == ExecutionStatus.COMPLETED

    @property
    def failed(self) -> bool:
        return not self.succeeded