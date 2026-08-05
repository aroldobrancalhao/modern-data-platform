"""
Modern Data Platform
Processing Framework

Console logger.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from typing import Any

import structlog

from data_platform.processing.logging.log_entry import LogEntry
from data_platform.processing.logging.logger import Logger


class ConsoleLogger(Logger):
    """
    Logger implementation backed by structlog.
    """

    def __init__(
        self,
        logger: Any | None = None,
    ) -> None:
        self._logger = logger or structlog.get_logger(
            "data_platform.processing",
        )

    def log(
        self,
        entry: LogEntry,
    ) -> None:
        bound = self._logger.bind(
            execution_id=entry.execution_id,
            pipeline_id=entry.pipeline_id,
            pipeline_name=entry.pipeline_name,
            stage_id=entry.stage_id,
            stage_name=entry.stage_name,
            duration=entry.duration,
            metadata=entry.metadata,
        )

        method = getattr(bound, entry.level.value.lower())

        method(
            entry.message,
            exc_info=entry.exception,
        )