from __future__ import annotations

from platform.providers.provider_registry import ProviderRegistry

from providers.aws.bootstrap import register as register_aws
from providers.databricks.bootstrap import register as register_databricks


def bootstrap() -> ProviderRegistry:
    """
    Creates and populates the provider registry.
    """
    registry = ProviderRegistry()

    register_aws(registry)
    register_databricks(registry)

    return registry
