from platform.providers.provider_registry import ProviderRegistry

from providers.databricks.compute.builder import (
    DatabricksComputeBuilder,
)


def register(
    registry: ProviderRegistry,
) -> None:

    registry.register(
        "databricks",
        DatabricksComputeBuilder,
    )
