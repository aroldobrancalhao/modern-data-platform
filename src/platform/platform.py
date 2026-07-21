from __future__ import annotations

from platform.bootstrap import bootstrap
from platform.config.settings import Settings
from platform.providers.provider import Provider
from platform.providers.provider_factory import ProviderFactory


class Platform:
    """
    Entry point for the Modern Data Platform.
    """

    def __init__(
        self,
        settings: Settings,
    ) -> None:

        self._settings = settings

        registry = bootstrap()

        self._factory = ProviderFactory(
            registry=registry,
            settings=settings,
        )

    @property
    def settings(self) -> Settings:
        return self._settings

    def storage(self) -> Provider:
        return self._factory.create(
            self._settings.storage_provider,
        )

    def catalog(self) -> Provider:
        return self._factory.create(
            self._settings.catalog_provider,
        )

    def compute(self) -> Provider:
        return self._factory.create(
            self._settings.compute_provider,
        )
