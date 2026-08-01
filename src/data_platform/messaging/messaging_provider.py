"""
Modern Data Platform

Messaging provider contract.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from data_platform.contracts.base_provider import BaseProvider
from data_platform.messaging.models import Message


class MessagingProvider(BaseProvider, ABC):
    """
    Contract implemented by messaging/event-streaming providers.

    A MessagingProvider is responsible only for producing and
    consuming messages against a topic (Apache Kafka, Amazon MSK,
    Azure Event Hubs, Google Pub/Sub, ...), exposing a
    provider-agnostic API.

    Per ADR-0008, this contract carries no orchestration, retry or
    Dead Letter Queue responsibility -- those belong to whoever
    consumes the Provider (e.g. a Stage that decides to publish a
    failed message to a retry topic, or commits offsets manually).
    """

    @abstractmethod
    def produce(
        self,
        topic: str,
        value: bytes,
        key: str | None = None,
        headers: dict[str, bytes] | None = None,
    ) -> None:
        """
        Publishes a message to a topic.
        """
        raise NotImplementedError

    @abstractmethod
    def consume(
        self,
        topic: str,
        group_id: str,
        timeout_seconds: float = 1.0,
    ) -> Message | None:
        """
        Polls a single message from a topic.

        Returns None if no message becomes available within
        timeout_seconds. This is a single poll, not a blocking loop --
        callers that want to keep consuming are responsible for
        calling this repeatedly.
        """
        raise NotImplementedError
