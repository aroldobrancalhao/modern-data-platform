"""
Modern Data Platform
Processing Framework

Console tracer.
"""

from __future__ import annotations

import logging

from data_platform.processing.tracing.trace import Trace
from data_platform.processing.tracing.tracer import Tracer


class ConsoleTracer(Tracer):
    """
    Console tracer implementation.
    """

    def __init__(
        self,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._logger = logger or logging.getLogger(__name__)

    def record(
        self,
        trace: Trace,
    ) -> None:
        self._logger.info(
            (
                "Trace execution_id=%s "
                "pipeline=%s "
                "duration=%s "
                "spans=%d"
            ),
            trace.execution_id,
            trace.pipeline_name,
            trace.duration,
            len(trace.spans),
        )