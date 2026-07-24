from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from data_platform.processing.shared.models.processing_result import (
    ProcessingResult,
)
from data_platform.processing.shared.models.processing_statistics import (
    ProcessingStatistics,
)


def test_processing_result(
    processing_result: ProcessingResult,
    statistics: ProcessingStatistics,
) -> None:
    assert processing_result.success is True
    assert processing_result.duration == timedelta(seconds=5)
    assert processing_result.statistics == statistics


def test_failed_result(
    statistics: ProcessingStatistics,
) -> None:
    result = ProcessingResult(
        success=False,
        duration=timedelta(seconds=1),
        statistics=statistics,
    )

    assert result.success is False


def test_model_is_frozen(
    processing_result: ProcessingResult,
) -> None:
    with pytest.raises(ValidationError):
        processing_result.success = False


def test_extra_fields_are_forbidden(
    statistics: ProcessingStatistics,
) -> None:
    with pytest.raises(ValidationError):
        ProcessingResult.model_validate(
            {
                "success": True,
                "duration": timedelta(seconds=1),
                "statistics": statistics,
                "extra_field": True,
            }
        )