"""
Modern Data Platform
Processing Framework

Unit tests for MessagingContextWriter.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.messaging.models import Message
from data_platform.processing.context_writers.messaging_context_writer import (
    MessagingContextWriter,
)
from data_platform.processing.core.context_keys.messaging_keys import (
    MessagingKeys,
)
from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-1",
        metadata=ExecutionMetadata(execution_id="execution-1"),
    )


def test_write_populates_topic_key_partition_and_offset_for_a_consumed_message() -> None:
    context = create_context()

    message = Message(
        topic="orders",
        key="order-1",
        value=b"payload",
        partition=2,
        offset=42,
    )

    MessagingContextWriter.write(message, context)

    assert context.get(MessagingKeys.TOPIC) == "orders"
    assert context.get(MessagingKeys.KEY) == "order-1"
    assert context.get(MessagingKeys.PARTITION) == 2
    assert context.get(MessagingKeys.OFFSET) == 42


def test_write_always_populates_topic() -> None:
    context = create_context()

    message = Message(
        topic="orders",
        key=None,
        value=b"payload",
    )

    MessagingContextWriter.write(message, context)

    assert context.get(MessagingKeys.TOPIC) == "orders"


def test_write_omits_key_when_message_has_no_key() -> None:
    context = create_context()

    message = Message(
        topic="orders",
        key=None,
        value=b"payload",
    )

    MessagingContextWriter.write(message, context)

    assert context.contains(MessagingKeys.KEY) is False


def test_write_omits_partition_and_offset_for_a_message_not_yet_produced() -> None:
    context = create_context()

    message = Message(
        topic="orders",
        key="order-1",
        value=b"payload",
    )

    MessagingContextWriter.write(message, context)

    assert context.contains(MessagingKeys.PARTITION) is False
    assert context.contains(MessagingKeys.OFFSET) is False


def test_write_never_sets_message_id() -> None:
    context = create_context()

    message = Message(
        topic="orders",
        key="order-1",
        value=b"payload",
        partition=2,
        offset=42,
    )

    MessagingContextWriter.write(message, context)

    assert context.contains(MessagingKeys.MESSAGE_ID) is False


def test_write_omits_consumer_group_when_not_provided() -> None:
    context = create_context()

    message = Message(
        topic="orders",
        key="order-1",
        value=b"payload",
        partition=2,
        offset=42,
    )

    MessagingContextWriter.write(message, context)

    assert context.contains(MessagingKeys.CONSUMER_GROUP) is False


def test_write_populates_consumer_group_when_provided() -> None:
    context = create_context()

    message = Message(
        topic="orders",
        key="order-1",
        value=b"payload",
        partition=2,
        offset=42,
    )

    MessagingContextWriter.write(
        message,
        context,
        group_id="bronze-consumers",
    )

    assert context.get(MessagingKeys.CONSUMER_GROUP) == "bronze-consumers"
