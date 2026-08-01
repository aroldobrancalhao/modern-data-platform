from data_platform.providers.provider_registry import ProviderRegistry

from integrations.kafka.messaging.kafka_builder import KafkaMessagingBuilder


def register(
    registry: ProviderRegistry,
) -> None:
    """
    Register Kafka providers.
    """

    registry.register(
        "kafka",
        KafkaMessagingBuilder,
    )
