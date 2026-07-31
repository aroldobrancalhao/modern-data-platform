"""
Modern Data Platform
Providers

Unit tests for ProviderFactory.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import pytest

from data_platform.config.settings import Settings
from data_platform.exceptions import ProviderNotFoundError
from data_platform.providers.provider import Provider
from data_platform.providers.provider_builder import ProviderBuilder
from data_platform.providers.provider_factory import ProviderFactory
from data_platform.providers.provider_registry import ProviderRegistry


class FakeProvider(Provider):
    """Minimal concrete Provider used only to exercise the factory."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings


class FakeProviderBuilder(ProviderBuilder[FakeProvider]):
    def build(self) -> FakeProvider:
        return FakeProvider(self._settings)


def create_factory(
    *,
    registry: ProviderRegistry | None = None,
    settings: Settings | None = None,
) -> ProviderFactory:
    return ProviderFactory(
        registry=registry if registry is not None else ProviderRegistry(),
        settings=settings if settings is not None else Settings(),
    )


def test_create_returns_instance_built_by_the_registered_builder() -> None:
    registry = ProviderRegistry()
    registry.register("fake", FakeProviderBuilder)

    factory = create_factory(registry=registry)

    provider = factory.create("fake")

    assert isinstance(provider, FakeProvider)


def test_create_passes_settings_through_to_the_builder() -> None:
    registry = ProviderRegistry()
    registry.register("fake", FakeProviderBuilder)

    settings = Settings()
    factory = create_factory(registry=registry, settings=settings)

    provider = factory.create("fake")

    assert isinstance(provider, FakeProvider)
    assert provider.settings is settings


def test_create_returns_a_new_instance_on_each_call() -> None:
    registry = ProviderRegistry()
    registry.register("fake", FakeProviderBuilder)

    factory = create_factory(registry=registry)

    first = factory.create("fake")
    second = factory.create("fake")

    assert first is not second


def test_create_raises_when_provider_not_registered() -> None:
    factory = create_factory()

    with pytest.raises(ProviderNotFoundError):
        factory.create("missing")
