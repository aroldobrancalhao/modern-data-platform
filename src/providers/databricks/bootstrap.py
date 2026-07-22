from data_platform.providers.provider_registry import ProviderRegistry

from providers.databricks.compute.builder import (
    DatabricksComputeBuilder,
)


def register(
    registry: ProviderRegistry,
) -> None:
    """
    Register Databricks providers.
    """

    registry.register(
        "databricks",
        DatabricksComputeBuilder,
    )