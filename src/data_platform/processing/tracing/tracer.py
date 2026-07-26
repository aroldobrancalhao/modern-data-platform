"""
Modern Data Platform
Processing Framework

Tracer interface.
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from data_platform.processing.tracing.trace import Trace


class Tracer(ABC):
    """
    Tracer abstraction.
    """

    @abstractmethod
    def record(
        self,
        trace: Trace,
    ) -> None:
        """
        Records a trace.
        """