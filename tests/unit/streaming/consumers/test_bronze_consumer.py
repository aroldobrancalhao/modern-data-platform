"""
Modern Data Platform

Unit tests for run_bronze_consumer.

Writes go through the real ``deltalake`` package against a local
``tmp_path`` (StorageConfig.bronze is monkeypatched to return a local
path instead of an S3 URI) -- only Kafka and Postgres are faked/
skipped, since neither is available to a unit test. This exercises the
real micro-batching, coercion and Delta-write path, not a mock of it.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pyarrow as pa
import pytest
from confluent_kafka import KafkaError, KafkaException
from deltalake import DeltaTable

from data_platform.messaging.messaging_provider import MessagingProvider
from data_platform.messaging.models import Message

from streaming.consumers import bronze_consumer
from streaming.consumers.bronze_consumer import run_bronze_consumer, topic_for

_SCHEMA = pa.schema(
    [
        ("id", pa.string()),
        ("amount", pa.decimal128(10, 2)),
    ]
)


def _envelope(entity: str, op: str, after: dict[str, Any]) -> bytes:
    envelope = {
        "schema": {
            "fields": [
                {
                    "field": "after",
                    "type": "struct",
                    "fields": [{"field": name} for name in after],
                }
            ]
        },
        "payload": {"op": op, "source": {"table": entity}, "after": after},
    }

    return json.dumps(envelope).encode("utf-8")


@dataclass
class FakeMessagingProvider(MessagingProvider):
    """
    In-memory MessagingProvider: one FIFO queue per (topic, group_id),
    plus a counter of commit() calls per pair -- enough to assert the
    consumer's buffering, flushing and offset-commit behaviour without
    a real Kafka broker.
    """

    queues: dict[tuple[str, str], list[bytes]] = field(default_factory=dict)

    commits: dict[tuple[str, str], int] = field(default_factory=dict)

    def enqueue(self, topic: str, group_id: str, value: bytes) -> None:
        self.queues.setdefault((topic, group_id), []).append(value)

    def produce(
        self,
        topic: str,
        value: bytes,
        key: str | None = None,
        headers: dict[str, bytes] | None = None,
    ) -> None:
        raise NotImplementedError

    def consume(
        self,
        topic: str,
        group_id: str,
        timeout_seconds: float = 1.0,
        auto_commit: bool = True,
    ) -> Message | None:
        queue = self.queues.get((topic, group_id))

        if not queue:
            return None

        return Message(topic=topic, key=None, value=queue.pop(0))

    def consume_batch(
        self,
        topic: str,
        group_id: str,
        max_messages: int,
        timeout_seconds: float = 1.0,
        auto_commit: bool = True,
    ) -> list[Message]:
        queue = self.queues.get((topic, group_id))

        if not queue:
            return []

        batch, queue[:] = queue[:max_messages], queue[max_messages:]

        return [Message(topic=topic, key=None, value=value) for value in batch]

    def commit(self, topic: str, group_id: str) -> None:
        key = (topic, group_id)
        self.commits[key] = self.commits.get(key, 0) + 1

    def consumer_lag(self, topic: str, group_id: str) -> int | None:
        """
        This fake has no partitions/offsets to speak of, so "lag" is
        approximated as the number of messages still queued for
        (topic, group_id) -- close enough to the real contract's
        intent (unconsumed backlog) for what run_bronze_consumer's
        tests need.
        """
        return len(self.queues.get((topic, group_id), []))


class _FakeClock:
    """
    Advances by ``step`` seconds on every call -- run_bronze_consumer
    keeps its buffering state local to a single call (by design: in
    production it is only ever called once and runs forever), so a
    test that wants to see a buffer age past _MAX_BATCH_AGE_SECONDS
    must do it within one continuous run_bronze_consumer call, not by
    pausing between two separate calls.
    """

    def __init__(self, step: float = 1.0) -> None:
        self._now = 0.0
        self._step = step

    def __call__(self) -> float:
        value = self._now
        self._now += self._step
        return value


@pytest.fixture(autouse=True)
def _bronze_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Routes every entity's Bronze Delta table to ``tmp_path/{entity}``
    instead of a real S3 bucket.
    """

    monkeypatch.setattr(
        bronze_consumer.StorageConfig,
        "bronze",
        classmethod(lambda cls, entity: str(tmp_path / entity)),
    )

    return tmp_path


@pytest.fixture(autouse=True)
def _schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bronze_consumer,
        "resolve_bronze_schema",
        lambda entity: _SCHEMA,
    )


def test_flushes_and_commits_once_the_batch_size_threshold_is_reached(
    tmp_path: Path,
) -> None:
    provider = FakeMessagingProvider()
    topic = topic_for("orders")

    batch_size = bronze_consumer._MAX_BATCH_SIZE

    for index in range(batch_size):
        provider.enqueue(
            topic,
            bronze_consumer._CONSUMER_GROUP_ID,
            _envelope(
                "orders",
                "c",
                {"id": f"order-{index}", "amount": 9.99},
            ),
        )

    run_bronze_consumer(
        provider,
        entities=("orders",),
        max_iterations=batch_size,
    )

    table = DeltaTable(str(tmp_path / "orders")).to_pyarrow_table()

    assert table.num_rows == batch_size
    assert provider.commits[(topic, bronze_consumer._CONSUMER_GROUP_ID)] == 1


def test_flushes_on_batch_age_before_reaching_the_size_threshold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bronze_consumer.time, "monotonic", _FakeClock())

    provider = FakeMessagingProvider()
    topic = topic_for("orders")

    provider.enqueue(
        topic,
        bronze_consumer._CONSUMER_GROUP_ID,
        _envelope("orders", "c", {"id": "order-1", "amount": 9.99}),
    )

    # The fake clock advances 1s per is_due() check, so the buffer
    # (opened on iteration 0, well short of the size threshold) ages
    # past _MAX_BATCH_AGE_SECONDS well within this many iterations,
    # all inside the same run_bronze_consumer call -- its buffering
    # state does not survive across separate calls (see _FakeClock).
    run_bronze_consumer(
        provider,
        entities=("orders",),
        max_iterations=int(bronze_consumer._MAX_BATCH_AGE_SECONDS) + 5,
    )

    table = DeltaTable(str(tmp_path / "orders")).to_pyarrow_table()

    assert table.num_rows == 1
    assert provider.commits[(topic, bronze_consumer._CONSUMER_GROUP_ID)] == 1


def test_malformed_message_is_skipped_without_blocking_later_messages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bronze_consumer.time, "monotonic", _FakeClock())

    provider = FakeMessagingProvider()
    topic = topic_for("orders")

    provider.enqueue(topic, bronze_consumer._CONSUMER_GROUP_ID, b"not-json")
    provider.enqueue(
        topic,
        bronze_consumer._CONSUMER_GROUP_ID,
        _envelope("orders", "c", {"id": "order-1", "amount": 9.99}),
    )

    run_bronze_consumer(
        provider,
        entities=("orders",),
        max_iterations=int(bronze_consumer._MAX_BATCH_AGE_SECONDS) + 5,
    )

    table = DeltaTable(str(tmp_path / "orders")).to_pyarrow_table()

    assert table.num_rows == 1
    assert table.to_pylist()[0]["id"] == "order-1"


def test_entities_flush_independently(tmp_path: Path) -> None:
    orders_topic = topic_for("orders")
    payments_topic = topic_for("payments")

    provider = FakeMessagingProvider()

    for index in range(bronze_consumer._MAX_BATCH_SIZE):
        provider.enqueue(
            orders_topic,
            bronze_consumer._CONSUMER_GROUP_ID,
            _envelope(
                "orders", "c", {"id": f"order-{index}", "amount": 1.0}
            ),
        )

    provider.enqueue(
        payments_topic,
        bronze_consumer._CONSUMER_GROUP_ID,
        _envelope("payments", "c", {"id": "payment-1", "amount": 2.0}),
    )

    run_bronze_consumer(
        provider,
        entities=("orders", "payments"),
        max_iterations=bronze_consumer._MAX_BATCH_SIZE,
    )

    orders_table = DeltaTable(str(tmp_path / "orders")).to_pyarrow_table()
    assert orders_table.num_rows == bronze_consumer._MAX_BATCH_SIZE
    assert provider.commits[(orders_topic, bronze_consumer._CONSUMER_GROUP_ID)] == 1

    # payments never reached the size threshold and 30s never elapsed
    # (the real clock barely moves during this test), so it must still
    # be buffered, not written.
    assert not (tmp_path / "payments").exists()
    assert (payments_topic, bronze_consumer._CONSUMER_GROUP_ID) not in provider.commits


def test_batch_write_failure_leaves_offsets_uncommitted_and_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeMessagingProvider()
    topic = topic_for("orders")

    for index in range(bronze_consumer._MAX_BATCH_SIZE):
        provider.enqueue(
            topic,
            bronze_consumer._CONSUMER_GROUP_ID,
            _envelope(
                "orders", "c", {"id": f"order-{index}", "amount": 1.0}
            ),
        )

    real_write_deltalake = bronze_consumer.write_deltalake

    calls = {"count": 0}

    def flaky_write(*args: Any, **kwargs: Any) -> None:
        calls["count"] += 1

        if calls["count"] == 1:
            raise RuntimeError("simulated transient S3 failure")

        real_write_deltalake(*args, **kwargs)

    monkeypatch.setattr(bronze_consumer, "write_deltalake", flaky_write)

    # Iteration batch_size - 1 (0-indexed) is where the buffer first
    # reaches the size threshold and the first (failing) flush is
    # submitted to the thread pool; the buffer stays intact on
    # failure, so it is still due on every iteration after that until
    # a flush finally succeeds. Unlike before flushes ran on a thread
    # pool, "one extra iteration" is not enough margin here: the retry
    # is only *submitted* once the main loop observes the first
    # attempt's Future as done(), and that observation can only happen
    # on iterations still inside this call's max_iterations budget --
    # ThreadPoolExecutor's own __exit__ (shutdown(wait=True)) guarantees
    # every *submitted* flush finishes before run_bronze_consumer()
    # returns, but not that a retry gets submitted at all if the loop
    # runs out of iterations before the worker thread is even
    # scheduled. Confirmed live: with only "+1" margin, this flaked
    # under real CPU contention (running alongside tests/integration/'s
    # heavier fixtures) even though it passed reliably in isolation.
    # A large margin costs nothing here -- each iteration where the
    # entity is still busy is just one cheap dict lookup + continue.
    run_bronze_consumer(
        provider,
        entities=("orders",),
        max_iterations=bronze_consumer._MAX_BATCH_SIZE + 200,
    )

    table = DeltaTable(str(tmp_path / "orders")).to_pyarrow_table()
    assert table.num_rows == bronze_consumer._MAX_BATCH_SIZE
    assert calls["count"] == 2
    assert provider.commits[(topic, bronze_consumer._CONSUMER_GROUP_ID)] == 1


def test_batch_commit_failure_does_not_crash_and_retries_next_cycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Reproduces the live incident that motivated this test: all 16
    consumer threads lost their partition assignment (transient Kafka
    DNS/network failure), and the resulting KafkaException out of
    provider.commit() -- previously uncaught -- killed the whole
    process. write_deltalake() itself is not flaky here; only commit()
    is, so a real write lands on the first (failing-to-commit)
    attempt, and the retry appends a second, duplicate copy of the
    same records -- the accepted cost of retrying a commit-only
    failure without clearing the buffer (see _flush()).
    """
    provider = FakeMessagingProvider()
    topic = topic_for("orders")

    for index in range(bronze_consumer._MAX_BATCH_SIZE):
        provider.enqueue(
            topic,
            bronze_consumer._CONSUMER_GROUP_ID,
            _envelope(
                "orders", "c", {"id": f"order-{index}", "amount": 1.0}
            ),
        )

    real_commit = provider.commit

    calls = {"count": 0}

    def flaky_commit(topic: str, group_id: str) -> None:
        calls["count"] += 1

        if calls["count"] == 1:
            raise KafkaException(
                KafkaError(
                    KafkaError._ASSIGNMENT_LOST,
                    "simulated lost assignment",
                )
            )

        real_commit(topic, group_id)

    monkeypatch.setattr(provider, "commit", flaky_commit)

    # Same margin reasoning as
    # test_batch_write_failure_leaves_offsets_uncommitted_and_retries:
    # the retry is only submitted once the main loop observes the
    # first attempt's Future as done(), which needs real iterations
    # inside the budget, not just "+1" -- see that test's comment.
    run_bronze_consumer(
        provider,
        entities=("orders",),
        max_iterations=bronze_consumer._MAX_BATCH_SIZE + 200,
    )

    table = DeltaTable(str(tmp_path / "orders")).to_pyarrow_table()
    assert table.num_rows == bronze_consumer._MAX_BATCH_SIZE * 2
    assert calls["count"] == 2
    assert provider.commits[(topic, bronze_consumer._CONSUMER_GROUP_ID)] == 1
