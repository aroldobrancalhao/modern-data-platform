from __future__ import annotations

import pytest
from pydantic import ValidationError

from data_platform.processing.shared.models.processing_statistics import (
    ProcessingStatistics,
)


def test_default_values() -> None:
    statistics = ProcessingStatistics()

    assert statistics.records_read == 0
    assert statistics.records_written == 0
    assert statistics.records_failed == 0
    assert statistics.bytes_read == 0
    assert statistics.bytes_written == 0


def test_custom_values(statistics: ProcessingStatistics) -> None:
    assert statistics.records_read == 100
    assert statistics.records_written == 98
    assert statistics.records_failed == 2
    assert statistics.bytes_read == 1024
    assert statistics.bytes_written == 980


def test_negative_values_raise_validation_error() -> None:
    with pytest.raises(ValidationError):
        ProcessingStatistics(records_read=-1)


def test_model_is_frozen(statistics: ProcessingStatistics) -> None:
    with pytest.raises(ValidationError):
        statistics.records_read = 10


def test_extra_fields_are_forbidden() -> None:
    with pytest.raises(ValidationError):
        ProcessingStatistics.model_validate(
            {
                "extra_field": 1,
            }
        )