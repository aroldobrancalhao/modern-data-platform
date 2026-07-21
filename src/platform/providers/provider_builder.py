from abc import ABC, abstractmethod

from platform.config.settings import Settings
from platform.providers.provider import Provider


class ProviderBuilder(ABC):
    def __init__(
        self,
        settings: Settings,
    ) -> None:
        self._settings = settings

    @abstractmethod
    def build(self) -> Provider:
        """
        Creates a provider.
        """
