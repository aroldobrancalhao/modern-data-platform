from __future__ import annotations

from typing import cast

from data_platform.bootstrap import bootstrap
from data_platform.config.settings import Settings
from data_platform.contracts.compute_provider import ComputeProvider
from data_platform.models.compute import Execution
from data_platform.models.compute import Workload
from data_platform.providers.provider import Provider
from data_platform.providers.provider_factory import ProviderFactory


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

    def compute(self) -> ComputeProvider:
        return cast(
            ComputeProvider,
            self._factory.create(
                self._settings.compute_provider,
            ),
        )

    def execute(
        self,
        workload: Workload,
    ) -> Execution:
        """
        Execute a workload using the configured compute provider.
        """

        return self.compute().execute(workload)