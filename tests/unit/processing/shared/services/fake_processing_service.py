from __future__ import annotations

from datetime import timedelta
from typing import Any

from data_platform.processing.shared.models.processing_context import (
    ProcessingContext,
)
from data_platform.processing.shared.models.processing_result import (
    ProcessingResult,
)
from data_platform.processing.shared.models.processing_statistics import (
    ProcessingStatistics,
)
from data_platform.processing.shared.services.base_processing_service import (
    BaseProcessingService,
)


class FakeProcessingService(BaseProcessingService):
    """
    Fake implementation used to validate the behavior of
    BaseProcessingService.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []

    def before_process(
        self,
        context: ProcessingContext,
    ) -> None:
        self.calls.append("before")

    def read(
        self,
        context: ProcessingContext,
    ) -> list[str]:
        self.calls.append("read")
        return ["john", "mary", "alice"]

    def transform(
        self,
        data: list[str],
        context: ProcessingContext,
    ) -> list[str]:
        self.calls.append("transform")
        return [item.upper() for item in data]

    def write(
        self,
        data: list[str],
        context: ProcessingContext,
    ) -> None:
        self.calls.append("write")

    def build_result(
        self,
        data: list[str],
        context: ProcessingContext,
    ) -> ProcessingResult:
        self.calls.append("build_result")

        return ProcessingResult(
            success=True,
            duration=timedelta(seconds=1),
            statistics=ProcessingStatistics(
                records_read=3,
                records_written=3,
            ),
        )

    def after_process(
        self,
        context: ProcessingContext,
        result: ProcessingResult | None,
    ) -> None:
        self.calls.append("after")