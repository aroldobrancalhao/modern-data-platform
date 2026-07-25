"""
Modern Data Platform
Processing Framework

Stage execution result.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass

from data_platform.processing.core.processing_result import ProcessingResult


@dataclass(
    frozen=True,
    eq=False,
    slots=True,
    kw_only=True,
)
class StageResult(ProcessingResult):
    """
    Result produced by a single Stage execution.

    Extends ProcessingResult with
    stage-specific execution information.
    """

    stage_id: str

    stage_name: str

    attempt: int = 1