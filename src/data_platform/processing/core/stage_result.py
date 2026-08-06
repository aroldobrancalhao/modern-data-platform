"""
Modern Data Platform
Processing Framework

Stage execution result.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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

    output: dict[str, Any] = field(default_factory=dict)
    """
    Stage-specific structured output (e.g. PostgresExtractionStage
    puts the landed object's ``uri``/``bucket``/``object_key`` here).

    Carried on the return value instead of published into the shared
    ProcessingContext (the previous pattern, still used by e.g.
    StorageContextWriter for sequential stages) specifically because
    a StageResult is naturally isolated per stage -- a coroutine's own
    return value can't collide with a sibling's, unlike a shared
    context key, which is what makes this safe for
    ParallelExecutor's concurrent stages within a group. Prefer this
    over a ContextWriter for any new output a caller needs back from a
    stage that might run inside a parallel group.
    """