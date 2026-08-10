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
        auto_commit: bool = True,
    ) -> Message | None:
        """
        Polls a single message from a topic.

        Returns None if no message becomes available within
        timeout_seconds. This is a single poll, not a blocking loop --
        callers that want to keep consuming are responsible for
        calling this repeatedly.

        ``auto_commit`` defaults to True, matching every caller before
        this parameter existed. Pass False when the caller intends to
        call ``commit()`` explicitly once the message (or a batch it
        belongs to) has been durably processed -- the underlying
        consumer for a given (topic, group_id) pair is created once
        and reused, so this only takes effect on the *first* consume()
        call for that pair; passing a different value on a later call
        for the same pair has no effect until the process restarts.
        """
        raise NotImplementedError

    @abstractmethod
    def consume_batch(
        self,
        topic: str,
        group_id: str,
        max_messages: int,
        timeout_seconds: float = 1.0,
        auto_commit: bool = True,
    ) -> list[Message]:
        """
        Polls up to ``max_messages`` from a topic in a single call.

        Returns as soon as at least one message is available, or an
        empty list if none becomes available within timeout_seconds --
        it does not block waiting for the full ``max_messages`` to
        fill (same "return whatever's ready" semantics as consume(),
        just for a batch instead of one message). Added alongside
        consume() rather than replacing it: consume() is a simpler
        contract for a caller that genuinely wants one message at a
        time, and changing its return type would be a breaking change
        for no benefit to that caller.

        Same ``auto_commit`` caveat as consume() -- only takes effect
        on the first call that resolves a consumer for (topic,
        group_id).
        """
        raise NotImplementedError

    @abstractmethod
    def commit(
        self,
        topic: str,
        group_id: str,
    ) -> None:
        """
        Commits offsets for the consumer resolved by a prior
        consume(topic, group_id, ...) call, up to its current
        position.

        Only meaningful after at least one consume() call for the same
        (topic, group_id) pair -- there is nothing to commit otherwise.
        Intended for callers that passed auto_commit=False to
        consume(), to confirm processing explicitly instead of relying
        on Kafka's periodic auto-commit.
        """
        raise NotImplementedError

    @abstractmethod
    def recover_from_lost_assignment(
        self,
        topic: str,
        group_id: str,
        error: Exception,
    ) -> bool:
        """
        Given an exception raised by a prior commit() call, discards
        and replaces the underlying consumer for (topic, group_id) if
        ``error`` reflects this provider's specific, unrecoverable
        group-membership-loss condition (Kafka: ``_ASSIGNMENT_LOST`` --
        the broker no longer considers this consumer a group member at
        all) -- one a plain retry cannot resolve, since the existing
        consumer keeps presenting the same stale/revoked membership to
        the broker no matter how many times commit() is retried
        against it (see docs/architecture/roadmap-next-steps.md,
        "commit-failure retry can livelock an entity permanently").

        Returns True if a rejoin was performed -- the caller (Bronze
        Consumer's ``_flush()``) is then responsible for abandoning the
        in-flight micro-batch (clearing its buffer) rather than
        retrying it with the now-discarded consumer, since the
        replacement consumer starts over from the last *committed*
        offset, not from whatever position the discarded one was at.

        Returns False (and does nothing) for any other error -- e.g. a
        transient network blip, or a write failure that never reached
        commit() at all -- where the caller's existing
        retry-without-rejoining behavior already tends to self-heal.
        """
        raise NotImplementedError

    @abstractmethod
    def consumer_lag(
        self,
        topic: str,
        group_id: str,
    ) -> int | None:
        """
        Returns the total consumer lag for a previously resolved
        (topic, group_id) pair -- the sum, across every partition
        currently assigned to that consumer, of (that partition's
        latest available offset - the consumer's current position in
        it).

        Returns None if (topic, group_id) hasn't been resolved yet by
        a prior consume() call -- same contract as commit().
        """
        raise NotImplementedError
