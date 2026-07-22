from data_platform.contracts.compute_provider import ComputeProvider
from data_platform.providers.provider_builder import ProviderBuilder

from integrations.databricks.compute.client import DatabricksClient
from integrations.databricks.compute.databricks_compute_provider import (
    DatabricksComputeProvider,
)
from integrations.databricks.core.databricks_context import DatabricksContext


class DatabricksComputeBuilder(
    ProviderBuilder[ComputeProvider],
):
    """
    Builds a Databricks compute provider.
    """

    def build(self) -> ComputeProvider:
        context = DatabricksContext()

        return DatabricksComputeProvider(
            DatabricksClient(
                context,
            ),
        )