"""
Modern Data Platform
Processing Framework

Metric identifier.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field

from data_platform.processing.core.value_object import ValueObject


@dataclass(
    frozen=True,
    eq=False,
    slots=True,
)
class MetricId(ValueObject):
    """
    Immutable identifier of a metric.

    Metrics are uniquely identified by:

    - name
    - description
    - tags
    """

    name: str
    description: str = ""

    tags: tuple[tuple[str, str], ...] = field(
        default_factory=tuple,
    )

    def __init__(
        self,
        name: str,
        description: str = "",
        tags: Mapping[str, str] | None = None,
    ) -> None:
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", description)

        normalized_tags = tuple(
            sorted((tags or {}).items())
        )

        object.__setattr__(
            self,
            "tags",
            normalized_tags,
        )

    def with_tag(
        self,
        key: str,
        value: str,
    ) -> MetricId:
        current = dict(self.tags)
        current[key] = value

        return MetricId(
            name=self.name,
            description=self.description,
            tags=current,
        )

    def has_tag(
        self,
        key: str,
    ) -> bool:
        return key in dict(self.tags)

    def get_tag(
        self,
        key: str,
        default: str | None = None,
    ) -> str | None:
        return dict(self.tags).get(
            key,
            default,
        )

    def tags_dict(self) -> dict[str, str]:
        return dict(self.tags)