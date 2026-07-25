from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.processing_context import ProcessingContext
from data_platform.processing.core.processing_result import ProcessingResult
from data_platform.processing.core.stage import Stage

from .hook_type import HookType


@dataclass(frozen=True, slots=True)
class HookContext:
    """Carries information about a lifecycle event.

    This object is emitted by the processing framework and consumed by
    external components such as logging, metrics, statistics, tracing,
    auditing and resilience policies.
    """

    hook_type: HookType
    pipeline: Pipeline
    processing_context: ProcessingContext

    stage: Stage | None = None
    result: ProcessingResult | None = None
    exception: Exception | None = None

    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))