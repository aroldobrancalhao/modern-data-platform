from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class KafkaSettings:
    """
    Kafka client configuration.

    ``bootstrap_servers`` defaults to "localhost:9092" -- the address
    the local Kafka broker (confluentinc/cp-kafka, docker compose)
    exposes on the host. Inside the Airflow containers, which share a
    docker network with the broker, the correct value is instead
    "kafka:9092" -- pass it explicitly when constructing KafkaSettings
    from that environment.
    """

    bootstrap_servers: str = "localhost:9092"
