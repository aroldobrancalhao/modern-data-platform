"""
Modern Data Platform
Processing Framework

Defines the result of a policy evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass

from data_platform.processing.core.value_object import (
    ValueObject,
)


@dataclass(frozen=True, slots=True)
class PolicyResult(ValueObject):
    """
    Represents the outcome of a policy evaluation.

    Parameters
    ----------
    continue_execution:
        Indicates whether execution may continue.

    retry:
        Indicates whether the current stage should be retried.

    cancel_pipeline:
        Indicates whether the pipeline should be cancelled.

    reason:
        Optional explanation for the decision.
    """

    continue_execution: bool = True

    retry: bool = False

    cancel_pipeline: bool = False

    reason: str | None = None

    def __post_init__(self) -> None:
        """
        Validates the policy decision.

        Invalid combinations are rejected to prevent
        contradictory execution states.
        """

        if self.cancel_pipeline and self.continue_execution:
            raise ValueError(
                "A cancelled pipeline cannot continue execution."
            )

        if self.cancel_pipeline and self.retry:
            raise ValueError(
                "A cancelled pipeline cannot request a retry."
            )

        if self.retry and not self.continue_execution:
            raise ValueError(
                "Retry requires execution to continue."
            )