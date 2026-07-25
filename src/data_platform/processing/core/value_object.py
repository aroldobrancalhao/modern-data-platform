"""
Modern Data Platform
Processing Framework

Base abstraction for immutable Value Objects.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from dataclasses import fields
from typing import Any


@dataclass(
    frozen=True,
    eq=False,
    slots=True,
)
class ValueObject(ABC):
    """
    Base class for immutable Value Objects.

    Value Objects are compared by their attributes
    rather than identity.
    """

    def __eq__(self, other: object) -> bool:
        if other.__class__ is not self.__class__:
            return False

        return all(
            getattr(self, field.name) == getattr(other, field.name)
            for field in fields(self)
        )

    def __hash__(self) -> int:
        return hash(
            tuple(
                getattr(self, field.name)
                for field in fields(self)
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            field.name: getattr(self, field.name)
            for field in fields(self)
        }

    def __repr__(self) -> str:
        values = ", ".join(
            f"{field.name}={getattr(self, field.name)!r}"
            for field in fields(self)
        )

        return f"{self.__class__.__name__}({values})"