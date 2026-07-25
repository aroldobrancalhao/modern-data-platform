"""
Modern Data Platform
Processing Framework

Pipeline execution result.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass

from data_platform.processing.core.processing_result import ProcessingResult
from data_platform.processing.core.stage_result import StageResult


@dataclass(frozen=True, slots=True)
class PipelineResult(ProcessingResult):
    """
    Result produced by a Pipeline execution.

    Aggregates every StageResult generated during the
    execution of a pipeline.
    """

    stage_results: tuple[StageResult, ...] = ()

    @property
    def total_stages(self) -> int:
        """
        Total number of executed stages.
        """
        return len(self.stage_results)

    @property
    def successful_stages(self) -> int:
        """
        Number of successfully executed stages.
        """
        return sum(
            1
            for result in self.stage_results
            if result.succeeded
        )

    @property
    def failed_stages(self) -> int:
        """
        Number of failed stages.
        """
        return sum(
            1
            for result in self.stage_results
            if result.failed
        )

    @property
    def last_result(self) -> StageResult | None:
        """
        Returns the last executed stage result.

        Returns
        -------
        StageResult | None
            The last stage result or None when no stages
            were executed.
        """
        if not self.stage_results:
            return None

        return self.stage_results[-1]

    @property
    def has_failures(self) -> bool:
        """
        Indicates whether at least one stage failed.
        """
        return self.failed_stages > 0