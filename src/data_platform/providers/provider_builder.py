from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Generic
from typing import TypeVar

from data_platform.config.settings import Settings
from data_platform.providers.provider import Provider

ProviderT = TypeVar(
    "ProviderT",
    bound=Provider,
)


class ProviderBuilder(
    ABC,
    Generic[ProviderT],
):
    """
    Base class for provider builders.
    """

    def __init__(
        self,
        settings: Settings,
    ) -> None:
        self._settings = settings

    @abstractmethod
    def build(self) -> ProviderT:
        """
        Creates a provider.
        """