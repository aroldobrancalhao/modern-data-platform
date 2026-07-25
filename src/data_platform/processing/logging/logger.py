"""
Modern Data Platform
Processing Framework

Logger abstraction.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from data_platform.processing.logging.log_entry import LogEntry


class Logger(ABC):
    """
    Base logger abstraction.
    """

    @abstractmethod
    def log(
        self,
        entry: LogEntry,
    ) -> None:
        """
        Writes a log entry.
        """