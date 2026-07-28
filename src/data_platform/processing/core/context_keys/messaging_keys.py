from enum import StrEnum, unique


@unique
class MessagingKeys(StrEnum):
    """Keys produced by messaging providers."""

    MESSAGE_ID = "messaging.message_id"

    KEY = "messaging.key"

    TOPIC = "messaging.topic"

    PARTITION = "messaging.partition"

    OFFSET = "messaging.offset"

    CONSUMER_GROUP = "messaging.consumer_group"