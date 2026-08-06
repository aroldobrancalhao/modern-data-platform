from __future__ import annotations

import pytest
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


# The 4 tests below construct real confluent_kafka Producer/Consumer
# objects against KafkaSettings()'s default bootstrap_servers
# ("kafka:9092"), a hostname that only resolves inside the docker
# network -- unlike test_settings_* above (pure KafkaSettings/
# dataclass logic, no network), these need the real broker reachable
# to behave as intended and were confirmed live to degrade badly
# without it (a stats_cb briefly added elsewhere in the codebase for
# an unrelated investigation made the unresolved-hostname retries
# stall for minutes -- see "Batch-poll (max_messages=25) validated"
# in docs/architecture/roadmap-next-steps.md). Marked individually
# rather than module-wide (unlike the dedicated tests/integration/
# kafka/*_real_kafka.py files) because this file is a genuine mix --
# module-wide real_kafka would also wrongly exclude the two
# network-free tests above from the default suite.
@pytest.mark.real_kafka
def test_producer_returns_a_confluent_kafka_producer() -> None:
    context = KafkaContext()

    assert isinstance(context.producer, Producer)


@pytest.mark.real_kafka
def test_producer_is_cached_across_accesses() -> None:
    context = KafkaContext()

    assert context.producer is context.producer


@pytest.mark.real_kafka
def test_create_consumer_returns_a_confluent_kafka_consumer() -> None:
    context = KafkaContext()

    assert isinstance(context.create_consumer("test-group"), Consumer)


@pytest.mark.real_kafka
def test_create_consumer_returns_a_new_instance_on_each_call() -> None:
    context = KafkaContext()

    first = context.create_consumer("test-group")
    second = context.create_consumer("test-group")

    assert first is not second
