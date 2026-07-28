"""
Modern Data Platform
Processing Framework

Stage abstraction.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from data_platform.processing.core.entity import Entity
from data_platform.processing.core.processing_context import ProcessingContext
from data_platform.processing.core.stage_result import StageResult


@dataclass(eq=False, slots=True)
class Stage(Entity[str], ABC):
    """
    Base abstraction for a processing stage.
    """

    name: str

    max_attempts: int = 3

    @abstractmethod
    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:
        """
        Executes the stage.
        """
        raise NotImplementedError