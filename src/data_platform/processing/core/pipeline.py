"""
Modern Data Platform
Processing Framework

Pipeline definition.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass

from data_platform.processing.core.entity import Entity
from data_platform.processing.core.stage import Stage


@dataclass(
    eq=False,
    slots=True,
)
class Pipeline(Entity[str]):
    """
    Immutable processing pipeline.

    A Pipeline is an ordered collection of stages that
    defines the execution flow.
    """

    name: str

    stages: tuple[Stage, ...]

    def __post_init__(self) -> None:
        """
        Validates pipeline invariants.
        """
        if not self.id:
            raise ValueError("Pipeline id cannot be empty.")

        if not self.name:
            raise ValueError("Pipeline name cannot be empty.")

        if not self.stages:
            raise ValueError("A pipeline must contain at least one stage.")

        stage_ids: set[str] = set()

        for stage in self.stages:
            if stage is None:
                raise ValueError("Pipeline cannot contain null stages.")

            if stage.id in stage_ids:
                raise ValueError(
                    f"Duplicate stage id detected: '{stage.id}'."
                )

            stage_ids.add(stage.id)

    def __iter__(self):
        return iter(self.stages)

    def __len__(self) -> int:
        return len(self.stages)

    @property
    def is_empty(self) -> bool:
        return len(self.stages) == 0

    @property
    def stage_count(self) -> int:
        return len(self.stages)