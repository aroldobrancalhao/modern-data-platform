from platform.providers.provider_builder import ProviderBuilder

from providers.databricks.compute.builder import (
    DatabricksComputeProvider,
)


class DatabricksComputeBuilder(ProviderBuilder):
    """
    Builds the Databricks compute provider.
    """

    def build(self) -> DatabricksComputeProvider:
        return DatabricksComputeProvider()