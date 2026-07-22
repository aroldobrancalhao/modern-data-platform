from __future__ import annotations

from data_platform.exceptions import (
    ProviderAlreadyRegisteredError,
    ProviderNotFoundError,
)
from data_platform.providers.provider_builder import ProviderBuilder


class ProviderRegistry:
    """
    Stores all provider builders registered in the platform.
    """

    def __init__(self) -> None:
        self._builders: dict[str, type[ProviderBuilder]] = {}

    def register(
        self,
        provider_name: str,
        builder_type: type[ProviderBuilder],
    ) -> None:
        """
        Registers a provider builder.
        """
        if provider_name in self._builders:
            raise ProviderAlreadyRegisteredError(provider_name)

        self._builders[provider_name] = builder_type

    def unregister(
        self,
        provider_name: str,
    ) -> None:
        """
        Removes a provider builder.
        """
        if provider_name not in self._builders:
            raise ProviderNotFoundError(provider_name)

        del self._builders[provider_name]

    def contains(
        self,
        provider_name: str,
    ) -> bool:
        """
        Returns True if the provider is registered.
        """
        return provider_name in self._builders

    def get(
        self,
        provider_name: str,
    ) -> type[ProviderBuilder]:
        """
        Returns the registered builder.
        """
        builder = self._builders.get(provider_name)

        if builder is None:
            raise ProviderNotFoundError(provider_name)

        return builder

    def providers(self) -> tuple[str, ...]:
        """
        Returns all registered providers.
        """
        return tuple(sorted(self._builders.keys()))

    def clear(self) -> None:
        """
        Removes all registered providers.
        """
        self._builders.clear()
