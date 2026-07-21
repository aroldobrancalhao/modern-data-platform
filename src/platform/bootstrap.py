from __future__ import annotations

from platform.providers.provider_registry import ProviderRegistry

from providers.aws.bootstrap import register as register_aws
from providers.databricks.bootstrap import register as register_databricks
from providers.local.bootstrap import register as register_local


def bootstrap() -> ProviderRegistry:
    """
    Creates and populates the provider registry.
    """
    registry = ProviderRegistry()

    register_aws(registry)
    register_databricks(registry)
    register_local(registry)

    return registry
