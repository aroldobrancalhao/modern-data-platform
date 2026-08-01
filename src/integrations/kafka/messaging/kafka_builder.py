from __future__ import annotations

from data_platform.providers.provider_builder import ProviderBuilder

from integrations.kafka.core.kafka_context import KafkaContext
from integrations.kafka.messaging.kafka_messaging_provider import (
    KafkaMessagingProvider,
)


class KafkaMessagingBuilder(ProviderBuilder[KafkaMessagingProvider]):
    """
    Builds a Kafka messaging provider.
    """

    def build(self) -> KafkaMessagingProvider:
        context = KafkaContext()

        return KafkaMessagingProvider(context)
