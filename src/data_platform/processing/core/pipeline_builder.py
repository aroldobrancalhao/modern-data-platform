"""
Modern Data Platform
Processing Framework

Pipeline builder.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.stage import Stage


class PipelineBuilder:
    """
    Fluent builder for immutable Pipeline instances.
    """

    def __init__(self, id: str) -> None:
        self._id = id
        self._name: str = id
        self._stages: list[Stage] = []

    def named(self, name: str) -> "PipelineBuilder":
        """
        Sets the pipeline display name.
        """
        self._name = name
        return self

    def add_stage(self, stage: Stage) -> "PipelineBuilder":
        """
        Adds a stage to the pipeline.
        """
        if stage is None:
            raise ValueError("Stage cannot be None.")

        self._stages.append(stage)
        return self

    def add_stages(self, *stages: Stage) -> "PipelineBuilder":
        """
        Adds multiple stages preserving their order.
        """
        for stage in stages:
            self.add_stage(stage)

        return self

    def build(self) -> Pipeline:
        """
        Creates an immutable Pipeline instance.
        """
        return Pipeline(
            id=self._id,
            name=self._name,
            stages=tuple(self._stages),
        )