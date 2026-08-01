"""
Modern Data Platform

Messaging domain models.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Message:
    """
    Represents a message published to, or consumed from, a messaging
    provider (Kafka, Amazon MSK, Azure Event Hubs, Google Pub/Sub,
    ...).

    A single model covers both directions instead of a separate
    "message to produce" / "message consumed" pair:
    MessagingProvider.produce() takes discrete arguments (topic,
    value, key, headers), not a Message instance, and consume() is
    the only place a Message actually flows through the contract --
    so there is no current call site that would benefit from a
    stricter, produce-only variant.

    ``partition`` and ``offset`` are always populated on a Message
    returned by ``consume()`` (Kafka always assigns them to a
    consumed record), but stay ``None`` when a Message is constructed
    before producing (the broker only decides both once the message
    is written). They are typed as optional rather than split into a
    subclass (e.g. a ConsumedMessage) to avoid a second model with no
    current caller -- introduce that stronger guarantee later, when
    an actual call site needs it.
    """

    topic: str

    key: str | None

    value: bytes

    partition: int | None = None

    offset: int | None = None

    headers: dict[str, bytes] = field(default_factory=dict)
