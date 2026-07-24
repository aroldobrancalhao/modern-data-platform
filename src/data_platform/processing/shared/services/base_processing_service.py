from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any

from data_platform.processing.shared.models.processing_context import (
    ProcessingContext,
)
from data_platform.processing.shared.models.processing_result import (
    ProcessingResult,
)


class BaseProcessingService(ABC):
    """
    Base class implementing the processing lifecycle
    using the Template Method pattern.
    """

    def run(
        self,
        context: ProcessingContext,
    ) -> ProcessingResult:
        """
        Execute the processing workflow.
        """

        result: ProcessingResult | None = None

        try:
            self.before_process(context)

            data = self.read(context)

            data = self.transform(
                data=data,
                context=context,
            )

            self.write(
                data=data,
                context=context,
            )

            result = self.build_result(
                data=data,
                context=context,
            )

            return result

        finally:
            self.after_process(
                context=context,
                result=result,
            )

    def before_process(
        self,
        context: ProcessingContext,
    ) -> None:
        """
        Hook executed before processing.
        """

    @abstractmethod
    def read(
        self,
        context: ProcessingContext,
    ) -> Any:
        """
        Read the source data.
        """

    @abstractmethod
    def transform(
        self,
        data: Any,
        context: ProcessingContext,
    ) -> Any:
        """
        Transform the input data.
        """

    @abstractmethod
    def write(
        self,
        data: Any,
        context: ProcessingContext,
    ) -> None:
        """
        Persist the processed data.
        """

    @abstractmethod
    def build_result(
        self,
        data: Any,
        context: ProcessingContext,
    ) -> ProcessingResult:
        """
        Build the processing result.
        """

    def after_process(
        self,
        context: ProcessingContext,
        result: ProcessingResult | None,
    ) -> None:
        """
        Hook executed after processing.
        """