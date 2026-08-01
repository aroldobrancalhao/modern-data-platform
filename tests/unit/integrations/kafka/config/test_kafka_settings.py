from __future__ import annotations

from integrations.kafka.config.kafka_settings import KafkaSettings


def test_bootstrap_servers_defaults_to_localhost() -> None:
    assert KafkaSettings().bootstrap_servers == "localhost:9092"


def test_bootstrap_servers_accepts_an_explicit_override() -> None:
    settings = KafkaSettings(bootstrap_servers="kafka:9092")

    assert settings.bootstrap_servers == "kafka:9092"
