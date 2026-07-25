"""
Modern Data Platform
Processing Framework

Processing execution context.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from data_platform.processing.core.entity import Entity
from data_platform.processing.core.execution_metadata import ExecutionMetadata


@dataclass(eq=False, slots=True)
class ProcessingContext(Entity[str]):
    """
    Shared execution context.

    The ProcessingContext stores the mutable execution state
    shared across every component participating in a pipeline
    execution.
    """

    metadata: ExecutionMetadata

    _values: dict[str, Any] = field(default_factory=dict, init=False)

    def set(self, key: str, value: Any) -> None:
        """
        Stores a value in the execution context.
        """
        self._values[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a value from the execution context.
        """
        return self._values.get(key, default)

    def remove(self, key: str) -> None:
        """
        Removes a value from the context.
        """
        self._values.pop(key, None)

    def contains(self, key: str) -> bool:
        """
        Checks whether a key exists.
        """
        return key in self._values

    def clear(self) -> None:
        """
        Removes every stored value.
        """
        self._values.clear()

    @property
    def values(self) -> dict[str, Any]:
        """
        Returns a read-only copy of the stored values.
        """
        return self._values.copy()