from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class KafkaSettings(BaseSettings):
    """
    Kafka client configuration.

    ``bootstrap_servers`` defaults to "localhost:9092" -- the address
    the local Kafka broker (confluentinc/cp-kafka, docker compose)
    exposes on the host, and what every out-of-container caller (dev
    shell, pytest) wants. Inside a container that shares the broker's
    docker network (Airflow, the Bronze Consumer), the correct value
    is "kafka:9092" instead -- read from the KAFKA_BOOTSTRAP_SERVER
    env var, which x-airflow-common-env and the bronze-consumer
    service both already set (docker-compose.yml).

    Previously a plain frozen dataclass with the same hardcoded
    default and no env var support at all -- KAFKA_BOOTSTRAP_SERVER
    existed on both services well before this class could read it,
    silently doing nothing. Never surfaced because no containerized
    production path actually exercised KafkaContext() until the
    Bronze Consumer was containerized (Sprint 13): the Airflow DAG's
    only task never touches Kafka.
    """

    bootstrap_servers: str = Field(
        default="localhost:9092",
        validation_alias="KAFKA_BOOTSTRAP_SERVER",
    )

    model_config = SettingsConfigDict(
        extra="ignore",
        # validation_alias restricts __init__ to the alias name only
        # by default -- populate_by_name additionally allows the
        # field's own Python name (bootstrap_servers=...), which
        # existing tests (and KafkaContext's own docstring/tests)
        # already construct explicitly, independent of the env var.
        populate_by_name=True,
    )
