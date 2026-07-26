"""
Modern Data Platform
Processing Framework

Execution policy context.
"""

from __future__ import annotations

from dataclasses import dataclass

from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.core.stage import (
    Stage,
)


@dataclass(slots=True, frozen=True)
class PolicyContext:
    """
    Context used during policy evaluation.

    This context is independent from the hook system and
    contains only the information required by execution
    policies.
    """

    stage: Stage

    processing_context: ProcessingContext

    attempt: int = 1