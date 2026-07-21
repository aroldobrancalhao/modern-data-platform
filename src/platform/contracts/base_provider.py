from abc import ABC

from platform.types import PlatformProvider


class BaseProvider(ABC):
    """
    Base class for every platform provider.
    """

    provider: PlatformProvider

    @property
    def name(self) -> str:
        return self.provider.value

    def initialize(self) -> None:
        """
        Initialize provider resources.

        Optional hook for providers that require setup.
        """
        return None

    def shutdown(self) -> None:
        """
        Release provider resources.

        Optional hook for cleanup.
        """
        return None
