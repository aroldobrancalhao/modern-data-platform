from __future__ import annotations

from data_platform.contracts.compute_provider import ComputeProvider
from data_platform.models.compute import Execution
from data_platform.models.compute import Workload

from providers.databricks.compute.client import DatabricksClient
from providers.databricks.compute.mapper import DatabricksComputeMapper


class DatabricksComputeProvider(ComputeProvider):
    """
    Compute provider backed by Databricks Jobs.
    """

    def __init__(
        self,
        client: DatabricksClient,
    ) -> None:
        self._client = client

    def execute(
        self,
        workload: Workload,
    ) -> Execution:

        run = self._client.run(workload)

        return DatabricksComputeMapper.to_execution(run)