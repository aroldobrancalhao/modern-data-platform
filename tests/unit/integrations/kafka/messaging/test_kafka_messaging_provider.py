"""
Modern Data Platform

Unit tests for KafkaMessagingProvider.recover_from_lost_assignment() --
the real consumer-discard-and-recreate mechanics behind the Bronze
Consumer livelock fix (see
tests/unit/streaming/consumers/test_bronze_consumer.py for the
behavioral tests against the fake provider, and
docs/architecture/roadmap-next-steps.md, "commit-failure retry can
livelock an entity permanently", for the incident this fixes).

No real Kafka broker involved -- KafkaContext is never touched by this
method, only the provider's own consumer cache, so a MagicMock stands
in for the cached confluent_kafka.Consumer (same style as
tests/unit/integrations/s3/storage/test_s3_storage_provider.py).

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from confluent_kafka import KafkaError, KafkaException

from integrations.kafka.core.kafka_context import KafkaContext
from integrations.kafka.messaging.kafka_messaging_provider import (
    KafkaMessagingProvider,
)

_TOPIC = "marketplace.marketplace.orders"

_GROUP_ID = "bronze-consumer"


@pytest.fixture
def provider() -> KafkaMessagingProvider:
    # KafkaContext is never touched by recover_from_lost_assignment()
    # (it only manipulates the provider's own _consumers cache), so a
    # MagicMock stands in rather than a real KafkaContext.
    return KafkaMessagingProvider(MagicMock(spec=KafkaContext))


def _assignment_lost() -> KafkaException:
    return KafkaException(
        KafkaError(KafkaError._ASSIGNMENT_LOST, "simulated lost assignment")
    )


def test_returns_false_and_leaves_the_cache_untouched_for_a_non_kafka_error(
    provider: KafkaMessagingProvider,
) -> None:
    consumer = MagicMock()
    provider._consumers[(_TOPIC, _GROUP_ID)] = consumer

    recovered = provider.recover_from_lost_assignment(
        _TOPIC, _GROUP_ID, error=RuntimeError("simulated S3 write failure")
    )

    assert recovered is False
    assert provider._consumers[(_TOPIC, _GROUP_ID)] is consumer
    consumer.close.assert_not_called()


def test_returns_false_for_a_kafka_error_that_is_not_assignment_lost(
    provider: KafkaMessagingProvider,
) -> None:
    consumer = MagicMock()
    provider._consumers[(_TOPIC, _GROUP_ID)] = consumer

    other_error = KafkaException(
        KafkaError(KafkaError._TRANSPORT, "simulated transient network failure")
    )

    recovered = provider.recover_from_lost_assignment(
        _TOPIC, _GROUP_ID, error=other_error
    )

    assert recovered is False
    assert provider._consumers[(_TOPIC, _GROUP_ID)] is consumer
    consumer.close.assert_not_called()


def test_discards_and_closes_the_cached_consumer_on_assignment_lost(
    provider: KafkaMessagingProvider,
) -> None:
    consumer = MagicMock()
    provider._consumers[(_TOPIC, _GROUP_ID)] = consumer

    recovered = provider.recover_from_lost_assignment(
        _TOPIC, _GROUP_ID, error=_assignment_lost()
    )

    assert recovered is True
    # The cache entry is gone -- the next _resolve_consumer() call for
    # this (topic, group_id) will build a brand new Consumer and
    # subscribe() it fresh, which is the actual rejoin.
    assert (_TOPIC, _GROUP_ID) not in provider._consumers
    consumer.close.assert_called_once()


def test_a_failing_close_does_not_prevent_the_consumer_from_being_discarded(
    provider: KafkaMessagingProvider,
) -> None:
    """
    _ASSIGNMENT_LOST means the broker already stopped considering this
    consumer a group member -- a clean leave-group on close() is not
    guaranteed to succeed, and recovery must not depend on it
    succeeding: what matters is that the stale reference is gone so a
    replacement gets built, not that this specific close() call was
    clean.
    """
    consumer = MagicMock()
    consumer.close.side_effect = KafkaException(
        KafkaError(KafkaError._STATE, "simulated close-on-a-dead-consumer failure")
    )
    provider._consumers[(_TOPIC, _GROUP_ID)] = consumer

    recovered = provider.recover_from_lost_assignment(
        _TOPIC, _GROUP_ID, error=_assignment_lost()
    )

    assert recovered is True
    assert (_TOPIC, _GROUP_ID) not in provider._consumers


def test_returns_true_even_if_no_consumer_was_ever_cached_for_the_pair(
    provider: KafkaMessagingProvider,
) -> None:
    """
    Defensive edge case -- shouldn't happen in practice (commit() is
    only ever called for a (topic, group_id) that already resolved a
    consumer), but recover_from_lost_assignment() must not raise if it
    somehow does: there's nothing to discard, so the (also lazy)
    _resolve_consumer() path just creates one the normal way on the
    next call, same as if this had never been called at all.
    """
    recovered = provider.recover_from_lost_assignment(
        _TOPIC, _GROUP_ID, error=_assignment_lost()
    )

    assert recovered is True
    assert (_TOPIC, _GROUP_ID) not in provider._consumers
