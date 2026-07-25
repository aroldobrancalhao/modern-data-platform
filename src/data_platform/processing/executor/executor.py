"""
Modern Data Platform
Processing Framework

Executor abstraction.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.pipeline_result import PipelineResult
from data_platform.processing.core.processing_context import ProcessingContext


class Executor(ABC):
    """
    Base abstraction for pipeline executors.

    An Executor is responsible for executing an entire Pipeline
    and returning its consolidated result.
    """

    @abstractmethod
    async def execute(
        self,
        pipeline: Pipeline,
        context: ProcessingContext,
    ) -> PipelineResult:
        """
        Executes a pipeline.

        Parameters
        ----------
        pipeline:
            Pipeline definition to execute.

        context:
            Shared execution context.

        Returns
        -------
        PipelineResult
            Consolidated execution result.
        """
        raise NotImplementedError