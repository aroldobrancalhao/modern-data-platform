from abc import ABC
from abc import abstractmethod

from data_platform.contracts.base_provider import BaseProvider
from data_platform.models.compute import Execution
from data_platform.models.compute import Workload


class ComputeProvider(BaseProvider, ABC):
    """
    Contract implemented by compute engines.

    A ComputeProvider is responsible only for executing workloads.

    Scheduling, retries, orchestration and workflow execution belong to
    external orchestrators such as Apache Airflow.
    """

    @abstractmethod
    def execute(
        self,
        workload: Workload,
    ) -> Execution:
        """
        Execute a workload.
        """