"""
Modern Data Platform
Processing Framework

Unit tests for LogLevel.
"""

from data_platform.processing.logging.log_level import LogLevel


def test_should_have_expected_values() -> None:
    assert LogLevel.DEBUG.value == "DEBUG"
    assert LogLevel.INFO.value == "INFO"
    assert LogLevel.WARNING.value == "WARNING"
    assert LogLevel.ERROR.value == "ERROR"
    assert LogLevel.CRITICAL.value == "CRITICAL"


def test_should_convert_to_string() -> None:
    assert str(LogLevel.INFO) == "INFO"