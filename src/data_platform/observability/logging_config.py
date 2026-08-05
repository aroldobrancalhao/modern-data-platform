"""
Modern Data Platform

Structured logging configuration (structlog).

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import logging
import os

import structlog

_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

_DEFAULT_LEVEL = "INFO"


def _level_from_env() -> str:
    """
    Resolves the minimum log level from the LOG_LEVEL environment
    variable, falling back to INFO for anything missing or invalid.
    """
    value = os.environ.get("LOG_LEVEL", "").strip().upper()

    return value if value in _LEVELS else _DEFAULT_LEVEL


def configure_logging(*, level: str | None = None) -> None:
    """
    Configures structlog processors for the current process.

    Idempotent -- safe to call multiple times.

    Level resolution order: explicit `level` argument > LOG_LEVEL
    environment variable > INFO default.
    """
    resolved = (level or "").strip().upper()

    if resolved not in _LEVELS:
        resolved = _level_from_env()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, resolved),
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
