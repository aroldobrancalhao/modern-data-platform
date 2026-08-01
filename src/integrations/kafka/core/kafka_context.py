from __future__ import annotations

from functools import cached_property

from confluent_kafka import Consumer, Producer

from integrations.kafka.config.kafka_settings import KafkaSettings


class KafkaContext:
    """
    Shared Kafka context.

    Responsible for creating the confluent-kafka Producer/Consumer
    clients from KafkaSettings.
    """

    def __init__(
        self,
        settings: KafkaSettings | None = None,
    ) -> None:
        self._settings = settings or KafkaSettings()

    @property
    def settings(self) -> KafkaSettings:
        return self._settings

    @cached_property
    def producer(self) -> Producer:
        """
        A single Producer shared across every topic: unlike Consumer,
        a Producer is not scoped to any particular topic/partition or
        consumer group, so there is no reason to create more than one.
        """
        return Producer(
            {
                "bootstrap.servers": self._settings.bootstrap_servers,
            }
        )

    def create_consumer(
        self,
        group_id: str,
    ) -> Consumer:
        """
        Creates a new Consumer configured for the given consumer
        group.

        Unlike ``producer``, this is a factory method rather than a
        cached property: a Consumer is scoped to a single group.id
        (and, once subscribed, a set of topics), so the caller is
        responsible for keeping and reusing the returned instance
        across repeated polls instead of creating a new one every
        time.
        """
        return Consumer(
            {
                "bootstrap.servers": self._settings.bootstrap_servers,
                "group.id": group_id,
                "auto.offset.reset": "earliest",
            }
        )
