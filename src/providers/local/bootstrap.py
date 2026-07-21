from platform.providers.provider_registry import ProviderRegistry

from providers.local.storage.local_storage_builder import (
    LocalStorageBuilder,
)


def register(
    registry: ProviderRegistry,
) -> None:

    registry.register(
        "local",
        LocalStorageBuilder,
    )
