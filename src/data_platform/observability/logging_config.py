"""
Modern Data Platform

Structured logging configuration (structlog).

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import logging
import os
import sys

import structlog

_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

_DEFAULT_LEVEL = "INFO"

# Sprint 13 close-out (platform CloudWatch log group): opt-in, additive
# shipping of the exact same JSON lines the console already prints to
# CloudWatch. Gated by env vars rather than always-on so nothing
# changes for callers that don't set them (e.g. local dev outside
# Docker, or tests) -- console output via PrintLoggerFactory below is
# untouched either way, this is a second destination, not a
# replacement.
#
# LOG_SINK picks the destination: "stdout" (console only, the default)
# or "cloudwatch" (console + CloudWatch, see cloudwatch_sink.py -- the
# only module that imports watchtower). When LOG_SINK is unset or
# invalid, the older LOG_CLOUDWATCH_ENABLED flag still decides, so
# every existing deployment (docker-compose.yml sets only that flag)
# behaves exactly as before.
_SINK_ENV = "LOG_SINK"
_SINK_STDOUT = "stdout"
_SINK_CLOUDWATCH = "cloudwatch"
_SINKS = {_SINK_STDOUT, _SINK_CLOUDWATCH}

_CLOUDWATCH_ENABLED_ENV = "LOG_CLOUDWATCH_ENABLED"
_CLOUDWATCH_LOG_GROUP_ENV = "LOG_CLOUDWATCH_LOG_GROUP"

_cloudwatch_logger: logging.Logger | None = None
_cloudwatch_broken = False


def _level_from_env() -> str:
    """
    Resolves the minimum log level from the LOG_LEVEL environment
    variable, falling back to INFO for anything missing or invalid.
    """
    value = os.environ.get("LOG_LEVEL", "").strip().upper()

    return value if value in _LEVELS else _DEFAULT_LEVEL


def _cloudwatch_enabled() -> bool:
    return os.environ.get(_CLOUDWATCH_ENABLED_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _sink_from_env() -> str:
    """
    Resolves the log sink: a valid LOG_SINK wins; otherwise the legacy
    LOG_CLOUDWATCH_ENABLED flag selects "cloudwatch", else "stdout".
    """
    value = os.environ.get(_SINK_ENV, "").strip().lower()

    if value in _SINKS:
        return value

    return _SINK_CLOUDWATCH if _cloudwatch_enabled() else _SINK_STDOUT


def _get_cloudwatch_logger() -> logging.Logger:
    """
    Lazily creates (once per process) the CloudWatch shipping logger
    (cloudwatch_sink.build_cloudwatch_logger). cloudwatch_sink -- and
    with it watchtower -- is imported here, only once the "cloudwatch"
    sink is actually in use.
    """
    global _cloudwatch_logger

    if _cloudwatch_logger is not None:
        return _cloudwatch_logger

    log_group = os.environ.get(_CLOUDWATCH_LOG_GROUP_ENV, "").strip()

    if not log_group:
        raise RuntimeError(
            f"CloudWatch log sink selected but {_CLOUDWATCH_LOG_GROUP_ENV} is empty"
        )

    from data_platform.observability.cloudwatch_sink import build_cloudwatch_logger

    _cloudwatch_logger = build_cloudwatch_logger(log_group)

    return _cloudwatch_logger


def _ship_to_cloudwatch(logger: object, method_name: str, event: str) -> str:
    """
    Structlog processor -- runs last, after JSONRenderer has already
    turned the event dict into the final JSON string. Ships that exact
    string to CloudWatch when enabled, then returns it unchanged so
    PrintLoggerFactory still prints it to the console exactly as
    before. A CloudWatch failure (network, IAM, watchtower's own
    background thread) must never crash or block the caller -- console
    logging is the one guarantee this module makes; CloudWatch
    shipping is best-effort on top of it. Stops retrying after the
    first failure per process (rather than failing, and printing a
    warning about it, on every single subsequent log line) -- a broken
    CloudWatch path degrades to console-only, silently after the one
    warning.
    """
    global _cloudwatch_broken

    if _sink_from_env() != _SINK_CLOUDWATCH or _cloudwatch_broken:
        return event

    try:
        _get_cloudwatch_logger().info(event)
    except Exception as exc:  # noqa: BLE001 -- shipping must never crash the caller
        _cloudwatch_broken = True
        sys.stderr.write(
            f"data_platform.observability: CloudWatch log shipping disabled "
            f"for the rest of this process, first failure was: {exc!r}\n"
        )

    return event


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
            # structlog.types.Processor is typed for a processor
            # anywhere in the chain (event: EventDict), but this one
            # is deliberately last, after JSONRenderer already turned
            # the event into a plain str -- the position guarantee
            # mypy can't see, not a real type mismatch at runtime.
            _ship_to_cloudwatch,  # type: ignore[list-item]
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, resolved),
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
