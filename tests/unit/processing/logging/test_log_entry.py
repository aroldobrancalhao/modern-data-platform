"""
Modern Data Platform
Processing Framework

Unit tests for LogEntry.
"""

from data_platform.processing.logging.log_entry import LogEntry
from data_platform.processing.logging.log_level import LogLevel


def test_should_create_log_entry() -> None:
    entry = LogEntry(
        level=LogLevel.INFO,
        message="Pipeline started.",
    )

    assert entry.level is LogLevel.INFO
    assert entry.message == "Pipeline started."


def test_should_store_metadata() -> None:
    entry = LogEntry(
        level=LogLevel.INFO,
        message="Message",
        extra={
            "key": "value",
        },
    )

    assert entry.metadata["key"] == "value"


def test_should_be_immutable() -> None:
    entry = LogEntry(
        level=LogLevel.INFO,
        message="Test",
    )

    assert entry.message == "Test"