from __future__ import annotations

from enum import Enum


class HookType(str, Enum):
    """Lifecycle events emitted during pipeline execution.

    These events allow external components (logging, metrics,
    statistics, tracing, auditing, etc.) to observe the execution
    without coupling them to the processing framework.
    """

    BEFORE_PIPELINE = "before_pipeline"
    AFTER_PIPELINE = "after_pipeline"
    PIPELINE_FAILED = "pipeline_failed"

    BEFORE_STAGE = "before_stage"
    AFTER_STAGE = "after_stage"
    STAGE_FAILED = "stage_failed"