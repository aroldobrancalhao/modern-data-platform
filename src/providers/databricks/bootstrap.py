from platform.providers.provider_registry import ProviderRegistry

from providers.databricks.compute.databricks_compute_builder import (
    DatabricksComputeBuilder,
)


def register(
    registry: ProviderRegistry,
) -> None:

    registry.register(
        "databricks",
        DatabricksComputeBuilder,
    )
