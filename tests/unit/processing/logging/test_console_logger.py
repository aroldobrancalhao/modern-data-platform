from unittest.mock import Mock

from data_platform.processing.logging.console_logger import (
    ConsoleLogger,
)
from data_platform.processing.logging.log_entry import LogEntry
from data_platform.processing.logging.log_level import LogLevel


def test_should_log_entry() -> None:
    logger = Mock()

    console = ConsoleLogger(
        logger=logger,
    )

    console.log(
        LogEntry(
            level=LogLevel.INFO,
            message="hello",
        )
    )

    logger.log.assert_called_once()