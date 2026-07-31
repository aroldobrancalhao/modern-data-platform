"""
Modern Data Platform
Providers

Unit tests for ProviderRegistry.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import pytest

from data_platform.config.settings import Settings
from data_platform.exceptions import (
    ProviderAlreadyRegisteredError,
    ProviderNotFoundError,
)
from data_platform.providers.provider import Provider
from data_platform.providers.provider_builder import ProviderBuilder
from data_platform.providers.provider_registry import ProviderRegistry


class FakeProvider(Provider):
    """Minimal concrete Provider used only to exercise the registry."""


class FakeProviderBuilder(ProviderBuilder[FakeProvider]):
    def build(self) -> FakeProvider:
        return FakeProvider()


class AnotherFakeProviderBuilder(ProviderBuilder[FakeProvider]):
    def build(self) -> FakeProvider:
        return FakeProvider()


def create_registry() -> ProviderRegistry:
    return ProviderRegistry()


def test_register_makes_provider_available() -> None:
    registry = create_registry()

    registry.register("fake", FakeProviderBuilder)

    assert registry.contains("fake") is True


def test_register_raises_when_provider_already_registered() -> None:
    registry = create_registry()

    registry.register("fake", FakeProviderBuilder)

    with pytest.raises(ProviderAlreadyRegisteredError):
        registry.register("fake", AnotherFakeProviderBuilder)


def test_unregister_removes_provider() -> None:
    registry = create_registry()

    registry.register("fake", FakeProviderBuilder)
    registry.unregister("fake")

    assert registry.contains("fake") is False


def test_unregister_raises_when_provider_not_found() -> None:
    registry = create_registry()

    with pytest.raises(ProviderNotFoundError):
        registry.unregister("missing")


def test_contains_returns_false_for_unregistered_provider() -> None:
    registry = create_registry()

    assert registry.contains("missing") is False


def test_contains_returns_true_for_registered_provider() -> None:
    registry = create_registry()

    registry.register("fake", FakeProviderBuilder)

    assert registry.contains("fake") is True


def test_get_returns_registered_builder_type() -> None:
    registry = create_registry()

    registry.register("fake", FakeProviderBuilder)

    assert registry.get("fake") is FakeProviderBuilder


def test_get_raises_when_provider_not_found() -> None:
    registry = create_registry()

    with pytest.raises(ProviderNotFoundError):
        registry.get("missing")


def test_get_returned_builder_can_be_instantiated_and_build() -> None:
    registry = create_registry()

    registry.register("fake", FakeProviderBuilder)

    builder_type = registry.get("fake")
    provider = builder_type(Settings()).build()

    assert isinstance(provider, FakeProvider)


def test_providers_returns_empty_tuple_when_none_registered() -> None:
    registry = create_registry()

    assert registry.providers() == ()


def test_providers_returns_all_registered_names_sorted() -> None:
    registry = create_registry()

    registry.register("zeta", FakeProviderBuilder)
    registry.register("alpha", AnotherFakeProviderBuilder)

    assert registry.providers() == ("alpha", "zeta")


def test_clear_removes_every_registered_provider() -> None:
    registry = create_registry()

    registry.register("fake", FakeProviderBuilder)
    registry.register("another", AnotherFakeProviderBuilder)

    registry.clear()

    assert registry.providers() == ()
    assert registry.contains("fake") is False
    assert registry.contains("another") is False


def test_register_after_clear_succeeds() -> None:
    registry = create_registry()

    registry.register("fake", FakeProviderBuilder)
    registry.clear()

    registry.register("fake", FakeProviderBuilder)

    assert registry.contains("fake") is True
