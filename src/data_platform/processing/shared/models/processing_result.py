from __future__ import annotations

from datetime import timedelta

from pydantic import BaseModel
from pydantic import ConfigDict

from data_platform.processing.shared.models.processing_statistics import (
    ProcessingStatistics,
)


class ProcessingResult(BaseModel):
    """
    Represents the outcome of a processing execution.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    success: bool

    duration: timedelta

    statistics: ProcessingStatistics