from data_platform.providers.provider_registry import ProviderRegistry

from integrations.airflow.workflow.airflow_builder import (
    AirflowWorkflowBuilder,
)


def register(
    registry: ProviderRegistry,
) -> None:
    """
    Register Airflow providers.
    """

    registry.register(
        "airflow",
        AirflowWorkflowBuilder,
    )