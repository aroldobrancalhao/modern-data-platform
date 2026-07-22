from __future__ import annotations

from data_platform.providers.provider_registry import ProviderRegistry

from integrations.aws.bootstrap import register as register_aws
from integrations.databricks.bootstrap import register as register_databricks


def bootstrap() -> ProviderRegistry:
    """
    Creates and populates the provider registry.
    """
    registry = ProviderRegistry()

    register_aws(registry)
    register_databricks(registry)

    return registry
