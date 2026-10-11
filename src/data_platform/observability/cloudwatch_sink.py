"""
Modern Data Platform

CloudWatch log sink -- the only place in data_platform that imports
watchtower. Imported by logging_config only when the "cloudwatch" sink
is selected (LOG_SINK, or the legacy LOG_CLOUDWATCH_ENABLED flag), so
the default "stdout" sink never loads it.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import logging

import watchtower


def build_cloudwatch_logger(log_group: str) -> logging.Logger:
    """
    Returns the stdlib logger wired to watchtower.CloudWatchLogHandler
    that ships to ``log_group`` (module.cloudwatch_platform,
    monitoring.tf). Kept entirely separate from structlog's own
    PrintLoggerFactory pipeline -- this logger is never used for
    console output, only as a shipping target logging_config's
    processor writes the already-rendered JSON line into.
    """
    logger = logging.getLogger("data_platform.observability.cloudwatch")
    logger.setLevel(logging.DEBUG)
    # Never hand these records to the root logger too -- this logger
    # exists solely to drive the CloudWatch handler, nothing else
    # should print them a second time.
    logger.propagate = False
    logger.addHandler(
        watchtower.CloudWatchLogHandler(
            log_group_name=log_group,
            # Default log_stream_name template (hostname/program/pid)
            # is what's wanted here: multiple entry points (bronze-
            # consumer, the one-off scripts, the Airflow bootstrap
            # script, DAG tasks) can ship to the same log group
            # without clobbering each other's streams, with no
            # per-caller configuration needed.
            create_log_group=False,
        )
    )

    return logger
