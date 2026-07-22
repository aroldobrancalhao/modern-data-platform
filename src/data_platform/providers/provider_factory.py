from __future__ import annotations

from data_platform.config.settings import Settings
from data_platform.providers.provider import Provider
from data_platform.providers.provider_registry import ProviderRegistry


class ProviderFactory:
    """
    Creates providers from registered builders.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        settings: Settings,
    ) -> None:
        self._registry = registry
        self._settings = settings

    def create(
        self,
        provider_name: str,
    ) -> Provider:

        builder_type = self._registry.get(provider_name)

        builder = builder_type(
            self._settings,
        )

        return builder.build()