from __future__ import annotations

from confluent_kafka import Consumer, Producer

from integrations.kafka.config.kafka_settings import KafkaSettings
from integrations.kafka.core.kafka_context import KafkaContext


def test_settings_default_to_a_fresh_kafka_settings_instance() -> None:
    context = KafkaContext()

    assert context.settings == KafkaSettings()


def test_settings_preserves_an_explicit_override() -> None:
    settings = KafkaSettings(bootstrap_servers="kafka:9092")

    context = KafkaContext(settings)

    assert context.settings is settings


def test_producer_returns_a_confluent_kafka_producer() -> None:
    context = KafkaContext()

    assert isinstance(context.producer, Producer)


def test_producer_is_cached_across_accesses() -> None:
    context = KafkaContext()

    assert context.producer is context.producer


def test_create_consumer_returns_a_confluent_kafka_consumer() -> None:
    context = KafkaContext()

    assert isinstance(context.create_consumer("test-group"), Consumer)


def test_create_consumer_returns_a_new_instance_on_each_call() -> None:
    context = KafkaContext()

    first = context.create_consumer("test-group")
    second = context.create_consumer("test-group")

    assert first is not second
