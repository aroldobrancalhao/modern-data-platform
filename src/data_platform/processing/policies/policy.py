"""
Modern Data Platform
Processing Framework

Base interface for execution policies.
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from data_platform.processing.events.hook_context import (
    HookContext,
)

from .policy_result import PolicyResult


class Policy(ABC):
    """
    Base class for execution policies.
    """

    @abstractmethod
    async def evaluate(
        self,
        context: HookContext,
    ) -> PolicyResult:
        """
        Evaluates the current execution context.

        Parameters
        ----------
        context:
            Current execution context.

        Returns
        -------
        PolicyResult
            Policy evaluation result.
        """