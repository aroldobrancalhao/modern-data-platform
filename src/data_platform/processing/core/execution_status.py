"""
Modern Data Platform
Processing Framework

Execution status definitions.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from enum import Enum


class ExecutionStatus(str, Enum):
    """
    Represents the lifecycle state of a processing execution.

    This enumeration is shared across the entire Processing
    Framework to provide a consistent execution model.
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"
    TIMEOUT = "TIMEOUT"
    RETRYING = "RETRYING"

    @property
    def is_finished(self) -> bool:
        """
        Indicates whether the execution reached a terminal state.
        """
        return self in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.SKIPPED,
            ExecutionStatus.TIMEOUT,
        }

    @property
    def is_success(self) -> bool:
        """
        Indicates whether the execution completed successfully.
        """
        return self is ExecutionStatus.COMPLETED

    @property
    def is_failure(self) -> bool:
        """
        Indicates whether the execution finished due to an error.
        """
        return self in {
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMEOUT,
        }

    @property
    def can_retry(self) -> bool:
        """
        Indicates whether the current state allows a retry.
        """
        return self in {
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMEOUT,
        }