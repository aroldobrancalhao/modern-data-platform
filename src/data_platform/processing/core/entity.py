"""
Modern Data Platform
Processing Framework

Base abstraction for domain Entities.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Generic, TypeVar


TId = TypeVar("TId")


@dataclass(
    eq=False,
    slots=True,
)
class Entity(ABC, Generic[TId]):
    """
    Base class for all domain entities.

    Entities are identified by their unique identifier
    rather than their attribute values.
    """

    id: TId

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return False

        return (
            self.__class__ is other.__class__
            and self.id == other.id
        )

    def __hash__(self) -> int:
        return hash((self.__class__, self.id))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r})"