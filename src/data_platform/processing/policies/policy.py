"""
Modern Data Platform
Processing Framework

Base interface for execution policies.
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from data_platform.processing.policies.policy_context import PolicyContext
from data_platform.processing.policies.policy_result import PolicyResult


class Policy(ABC):
    """
    Base class for execution policies.
    """

    @abstractmethod
    async def evaluate(
        self,
        context: PolicyContext,
    ) -> PolicyResult:
        """
        Evaluates the current execution context.

        Parameters
        ----------
        context:
            Current policy context.

        Returns
        -------
        PolicyResult
            Policy evaluation result.
        """