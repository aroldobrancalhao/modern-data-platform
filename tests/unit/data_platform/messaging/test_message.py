"""
Modern Data Platform

Unit tests for the Message domain model.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.messaging.models import Message


def test_message_carries_topic_key_and_value() -> None:
    message = Message(
        topic="orders",
        key="order-1",
        value=b"payload",
    )

    assert message.topic == "orders"
    assert message.key == "order-1"
    assert message.value == b"payload"


def test_message_defaults_partition_and_offset_to_none() -> None:
    message = Message(
        topic="orders",
        key="order-1",
        value=b"payload",
    )

    assert message.partition is None
    assert message.offset is None


def test_message_accepts_a_none_key() -> None:
    message = Message(
        topic="orders",
        key=None,
        value=b"payload",
    )

    assert message.key is None


def test_message_defaults_headers_to_an_empty_dict() -> None:
    message = Message(
        topic="orders",
        key="order-1",
        value=b"payload",
    )

    assert message.headers == {}


def test_message_preserves_partition_offset_and_headers_when_consumed() -> None:
    message = Message(
        topic="orders",
        key="order-1",
        value=b"payload",
        partition=2,
        offset=42,
        headers={"trace-id": b"abc123"},
    )

    assert message.partition == 2
    assert message.offset == 42
    assert message.headers == {"trace-id": b"abc123"}


def test_message_is_frozen() -> None:
    message = Message(
        topic="orders",
        key="order-1",
        value=b"payload",
    )

    try:
        message.topic = "other"  # type: ignore[misc]
        raised = False
    except AttributeError:
        raised = True

    assert raised is True
