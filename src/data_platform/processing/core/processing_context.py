"""
Modern Data Platform
Processing Framework

Processing execution context.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
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

    Context values must be addressed using the ContextKeys enums
    (StrEnum). Plain strings are not accepted as keys.
    """

    metadata: ExecutionMetadata

    _values: dict[str, Any] = field(default_factory=dict, init=False)

    @staticmethod
    def _normalize_key(key: StrEnum) -> str:
        """
        Normalizes a ContextKeys member to its string value.
        """
        return key.value

    def set(self, key: StrEnum, value: Any) -> None:
        """
        Stores a value in the execution context.
        """
        self._values[self._normalize_key(key)] = value

    def get(
        self,
        key: StrEnum,
        default: Any = None,
    ) -> Any:
        """
        Retrieves a value from the execution context.
        """
        return self._values.get(
            self._normalize_key(key),
            default,
        )

    def remove(self, key: StrEnum) -> None:
        """
        Removes a value from the context.
        """
        self._values.pop(
            self._normalize_key(key),
            None,
        )

    def contains(self, key: StrEnum) -> bool:
        """
        Checks whether a key exists.
        """
        return self._normalize_key(key) in self._values

    def clear(self) -> None:
        """
        Removes every stored value.
        """
        self._values.clear()

    @property
    def values(self) -> dict[str, Any]:
        """
        Returns a copy of the stored values.
        """
        return self._values.copy()