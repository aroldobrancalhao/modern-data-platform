"""
Modern Data Platform
Processing Framework

Console logger.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import logging

from data_platform.processing.logging.log_entry import LogEntry
from data_platform.processing.logging.log_level import LogLevel
from data_platform.processing.logging.logger import Logger


_LEVEL_MAP = {
    LogLevel.DEBUG: logging.DEBUG,
    LogLevel.INFO: logging.INFO,
    LogLevel.WARNING: logging.WARNING,
    LogLevel.ERROR: logging.ERROR,
    LogLevel.CRITICAL: logging.CRITICAL,
}


class ConsoleLogger(Logger):
    """
    Logger implementation backed by the standard
    Python logging module.
    """

    def __init__(
        self,
        logger: logging.Logger | None = None,
    ) -> None:
        self._logger = logger or logging.getLogger(
            "data_platform.processing",
        )

    def log(
        self,
        entry: LogEntry,
    ) -> None:
        self._logger.log(
            _LEVEL_MAP[entry.level],
            entry.message,
            extra={
                "execution_id": entry.execution_id,
                "pipeline_id": entry.pipeline_id,
                "pipeline_name": entry.pipeline_name,
                "stage_id": entry.stage_id,
                "stage_name": entry.stage_name,
                "duration": entry.duration,
                "metadata": entry.metadata,
            },
            exc_info=entry.exception,
        )