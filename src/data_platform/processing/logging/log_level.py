"""
Modern Data Platform
Processing Framework

Log levels.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from enum import StrEnum


class LogLevel(StrEnum):
    """
    Supported log levels.
    """

    DEBUG = "DEBUG"

    INFO = "INFO"

    WARNING = "WARNING"

    ERROR = "ERROR"

    CRITICAL = "CRITICAL"