from __future__ import annotations

from data_platform.providers.provider_registry import ProviderRegistry

from integrations.aws.bootstrap import register as register_aws
from integrations.databricks.bootstrap import register as register_databricks
from integrations.airflow.bootstrap import register as register_airflow
from integrations.kafka.bootstrap import register as register_kafka


def bootstrap() -> ProviderRegistry:
    """
    Creates and populates the provider registry.
    """
    registry = ProviderRegistry()

    register_aws(registry)
    register_databricks(registry)
    register_airflow(registry)
    register_kafka(registry)

    return registry