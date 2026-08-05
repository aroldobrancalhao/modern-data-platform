"""
Modern Data Platform
Processing Framework

Console tracer.
"""

from __future__ import annotations

from typing import Any

import structlog

from data_platform.processing.tracing.trace import Trace
from data_platform.processing.tracing.tracer import Tracer


class ConsoleTracer(Tracer):
    """
    Console tracer implementation.
    """

    def __init__(
        self,
        *,
        logger: Any | None = None,
    ) -> None:
        self._logger = logger or structlog.get_logger(__name__)

    def record(
        self,
        trace: Trace,
    ) -> None:
        self._logger.bind(
            execution_id=trace.execution_id,
            pipeline_name=trace.pipeline_name,
            duration=trace.duration,
            spans=len(trace.spans),
        ).info("trace_recorded")