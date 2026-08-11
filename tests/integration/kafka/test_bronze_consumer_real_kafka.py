"""
Modern Data Platform

Real-Kafka end-to-end test for the Bronze Consumer.

Proves the full streaming flow closes end to end against real local
infrastructure (docker compose): a synthetic row inserted into the
real Postgres ``marketplace.carriers`` table is picked up by the real
Debezium connector, lands on the real Kafka topic
``marketplace.marketplace.carriers``, and is consumed, schema-resolved
(against the real Postgres information_schema) and written to a real
Delta table by run_bronze_consumer -- not a fake of any of these.

Only the Delta write target is redirected, from the real S3 bucket to
a local tmp_path: nothing here is specific to S3 (StorageConfig.bronze
is a one-line URI builder, already covered by the batch flow and by
this module's own unit tests), and it keeps this test from creating
`carriers`' very first real Bronze table with a single synthetic row.

A fresh, unique consumer group is used each run, but -- unlike this
test's earlier version -- it does **not** replay the topic from the
earliest offset: `_seed_consumer_group_at_tail()` below joins that
group and commits its position at the topic's real current tail
*before* the Postgres insert happens, so `run_bronze_consumer`'s own
consumer (created later, same group.id) starts from that pre-committed
position instead of "earliest" -- Kafka only ever applies
`auto.offset.reset` when no committed offset exists yet for a group,
so seeding one first bypasses it entirely. This test now proves
exactly what its name says -- "a new row flows through" -- without any
dependence on how much history `marketplace.marketplace.carriers`
happens to already hold (see docs/architecture/roadmap-next-steps.md
for the investigation that found the old earliest-replay design
couldn't keep up with the topic's own permanent, unbounded growth --
every run, including every run of this test itself, leaves 2 messages
behind forever, with no cleanup tied to the Postgres row's own
deletion in the `finally` block below).

carriers is the target entity: only 5 seed rows today (no risk of
competing with the 137k+-row entities), and every one of its columns
(uuid, varchar, boolean, timestamptz) already maps cleanly in
_DATA_TYPE_TO_ARROW, so this proves the wiring without also depending
on the double-to-Decimal path (that's covered on its own by
test_bronze_schema.py's coerce_record tests).

**_MAX_BATCH_SIZE/_MAX_BATCH_AGE_SECONDS/_MAX_POLL_ITERATIONS, why these
specific values (found stale and re-measured live, not guessed):**
`_MAX_BATCH_SIZE` matches production's own `_MAX_POLL_BATCH_SIZE`
(25). `_MAX_BATCH_AGE_SECONDS` is cut down from production's 30s to
3.0s so a trailing partial batch (this test's own 1-2 new messages
will essentially never fill a 25-record buffer) flushes promptly
instead of sitting for a real 30s. `_MAX_POLL_ITERATIONS` is 500 --
now, since `_seed_consumer_group_at_tail()` (see above) makes this
test's consumer start from the topic's real tail rather than
replaying its full history, that number is no longer sized against
backlog growth at all (a previous version of this test *was* fighting
exactly that -- the topic's own permanent, unbounded-in-practice
growth outgrowing a fixed iteration budget, see
docs/architecture/roadmap-next-steps.md for that investigation and
why it's resolved by the tail-seeding fix, not by raising this number
further). What 500 still buys headroom against is a real, separate,
per-flush cost: `run_bronze_consumer`'s round-robin loop busy-waits
(`time.sleep(0); continue`) while a flush is in flight on a worker
thread, and with only one entity under test, every one of those spins
counts against this budget too (measured directly elsewhere this same
session: ~270ms per flush cycle, translating to hundreds of spin
iterations at native Python loop speed -- see the same roadmap entry).
This test now needs at most 1-2 such cycles (not "however many it
takes to drain the topic's full history"), so 500 is now a generous
multiple of what a real run needs, not a number chosen against a
specific worst case.

**Honest status**: root-caused and fixed by
`_seed_consumer_group_at_tail()` -- validated with 10 consecutive
isolated live runs (see docs/architecture/roadmap-next-steps.md for
the exact pass count) after previously failing consistently under the
old earliest-replay design, whose failure mode was entirely explained
by the topic's real, measured backlog outgrowing this test's iteration
budget, not by any `run_bronze_consumer` bug.

Reuses the `real_kafka` marker, excluded from the default suite. Run
it explicitly with:

    uv run pytest tests/integration/kafka/test_bronze_consumer_real_kafka.py -m real_kafka -v

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import psycopg
import pytest
from confluent_kafka import Consumer, TopicPartition
from deltalake import DeltaTable

from data_platform.bootstrap import bootstrap
from data_platform.config.settings import Settings
from data_platform.messaging.messaging_provider import MessagingProvider
from data_platform.providers.provider_factory import ProviderFactory
from data_platform.storage.config import StorageConfig

from integrations.kafka.config.kafka_settings import KafkaSettings
from integrations.postgres.config import PostgresSettings
from streaming.consumers import bronze_consumer
from streaming.consumers.bronze_consumer import run_bronze_consumer, topic_for

pytestmark = pytest.mark.real_kafka

ENTITY = "carriers"

_MAX_POLL_ITERATIONS = 500

# How long _seed_consumer_group_at_tail() waits for the broker to
# finish a fresh consumer group's partition assignment before giving
# up -- assignment is asynchronous (a real group-join round-trip), so
# a plain immediate poll() can't be trusted to have one yet. 10s is
# generous for a local single-broker docker-compose Kafka (this step
# is consistently sub-second in practice); failing loudly with a clear
# message here beats a confusing downstream assertion failure if the
# broker is ever unusually slow to rebalance.
_ASSIGNMENT_TIMEOUT_SECONDS = 10.0


def _seed_consumer_group_at_tail(topic: str, group_id: str) -> None:
    """
    Joins ``group_id`` and commits its position at ``topic``'s real
    current tail (the high watermark of every partition), then closes
    the consumer -- so a *later* consumer resolved for the same
    (topic, group_id) pair (i.e. run_bronze_consumer's own, created
    inside the test body below) starts from that pre-committed
    position instead of replaying the topic's full history.

    This only works because Kafka applies `auto.offset.reset` (see
    KafkaContext.create_consumer, hardcoded to "earliest" -- correct
    for production's real Bronze Consumer group, which should replay
    from the start on its very first-ever run) exclusively when *no*
    committed offset exists yet for a group. Seeding one here first
    means that default is never consulted for this test's group at
    all -- not a config override, just winning the race deliberately
    instead of leaving it to chance.

    Deliberately bypasses the MessagingProvider abstraction and talks
    to confluent-kafka directly: this is a test-only concern (durably
    pre-committing a tail position before the code under test ever
    runs), not something any real caller of MessagingProvider needs,
    so it doesn't belong on that contract.
    """

    consumer = Consumer(
        {
            "bootstrap.servers": KafkaSettings().bootstrap_servers,
            "group.id": group_id,
            "enable.auto.commit": False,
        }
    )

    try:
        consumer.subscribe([topic])

        deadline = time.monotonic() + _ASSIGNMENT_TIMEOUT_SECONDS

        assignment: list[TopicPartition] = []

        while not assignment:
            if time.monotonic() > deadline:
                raise RuntimeError(
                    f"Consumer group {group_id!r} was not assigned any "
                    f"partition of {topic!r} within "
                    f"{_ASSIGNMENT_TIMEOUT_SECONDS}s -- cannot seed a "
                    "tail position."
                )

            consumer.poll(0.5)

            assignment = consumer.assignment()

        tail_offsets: list[TopicPartition] = []

        for partition in assignment:
            # cached=False: this must be the real current tail at the
            # moment of seeding, not a possibly-stale cached value
            # (see KafkaMessagingProvider.consumer_lag's own docstring
            # for when cached=True is fine instead -- this isn't that
            # case, it only runs once per test). None on a real
            # request timeout, per get_watermark_offsets' own
            # contract -- not expected against a local single-broker
            # docker-compose Kafka, but guarded rather than silently
            # indexed into.
            watermarks = consumer.get_watermark_offsets(
                partition, timeout=_ASSIGNMENT_TIMEOUT_SECONDS, cached=False
            )

            if watermarks is None:
                raise RuntimeError(
                    f"Timed out fetching watermark offsets for "
                    f"{partition.topic!r} partition {partition.partition} "
                    "-- cannot seed a tail position."
                )

            _low, high = watermarks

            tail_offsets.append(
                TopicPartition(partition.topic, partition.partition, high)
            )

        consumer.commit(offsets=tail_offsets, asynchronous=False)
    finally:
        consumer.close()


@pytest.fixture
def postgres_connection() -> Iterator[psycopg.Connection]:
    settings = PostgresSettings()

    with psycopg.connect(
        host=settings.host,
        port=settings.port,
        dbname=settings.database,
        user=settings.user,
        password=settings.password,
    ) as connection:
        yield connection


@pytest.fixture
def messaging_provider() -> MessagingProvider:
    provider_factory = ProviderFactory(
        registry=bootstrap(),
        settings=Settings(),
    )

    return cast(MessagingProvider, provider_factory.create("kafka"))


@pytest.fixture
def bronze_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(
        StorageConfig,
        "bronze",
        classmethod(lambda cls, entity: str(tmp_path / entity)),
    )

    return tmp_path


@pytest.fixture(autouse=True)
def group_id(monkeypatch: pytest.MonkeyPatch) -> str:
    """
    Generates this run's unique consumer group id, patches
    bronze_consumer's module-level constants to use it (plus the
    batch-size/age tuning below), and returns the id itself so the
    test body can seed it at the topic's tail before the Postgres
    insert (see _seed_consumer_group_at_tail) -- autouse=True still
    applies these patches even for a test that doesn't request this
    fixture by name, but this one does, specifically for the id.

    _MAX_BATCH_SIZE: matches production's own _MAX_POLL_BATCH_SIZE
    (25), not 1 -- and _MAX_BATCH_AGE_SECONDS is cut way down from
    production's 30s to 3s. Both together, not either alone -- see
    this module's own docstring for why (measured live: 1 causes
    ~30x iteration overhead per message from run_bronze_consumer's
    busy-wait on an in-flight flush; a bigger batch size alone then
    leaves a trailing partial batch stuck on the real, un-patched
    30s age timeout).
    """
    monkeypatch.setattr(
        bronze_consumer, "_MAX_BATCH_SIZE", bronze_consumer._MAX_POLL_BATCH_SIZE
    )
    monkeypatch.setattr(bronze_consumer, "_MAX_BATCH_AGE_SECONDS", 3.0)

    generated_group_id = f"bronze-consumer-e2e-test-{uuid.uuid4().hex}"

    monkeypatch.setattr(
        bronze_consumer,
        "_CONSUMER_GROUP_ID",
        generated_group_id,
    )

    return generated_group_id


def test_postgres_change_flows_through_debezium_and_kafka_into_bronze(
    postgres_connection: psycopg.Connection,
    messaging_provider: MessagingProvider,
    bronze_path: Path,
    group_id: str,
) -> None:
    carrier_code = f"TEST-{uuid.uuid4().hex[:12]}"
    carrier_name = "Bronze Consumer E2E Test Carrier"

    # Must happen before the Postgres insert below -- see
    # _seed_consumer_group_at_tail's own docstring for why the
    # ordering is what actually makes this work.
    _seed_consumer_group_at_tail(topic_for(ENTITY), group_id)

    with postgres_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO marketplace.carriers (code, name)
            VALUES (%s, %s)
            RETURNING carrier_id
            """,
            (carrier_code, carrier_name),
        )
        carrier_id = cursor.fetchone()[0]

    postgres_connection.commit()

    try:
        run_bronze_consumer(
            messaging_provider,
            entities=(ENTITY,),
            max_iterations=_MAX_POLL_ITERATIONS,
        )

        table_path = bronze_path / ENTITY

        if not table_path.exists():
            raise AssertionError(
                f"No Bronze write for '{ENTITY}' after "
                f"{_MAX_POLL_ITERATIONS} poll iterations -- the "
                "Debezium change event never arrived in time."
            )

        rows = DeltaTable(str(table_path)).to_pyarrow_table().to_pylist()

        matching = [row for row in rows if row["code"] == carrier_code]

        assert len(matching) == 1
        assert matching[0]["name"] == carrier_name
        assert matching[0]["carrier_id"] == str(carrier_id)
        assert matching[0]["is_active"] is True

        # Real Debezium/Kafka envelope, real resolve_bronze_schema()
        # call (not monkeypatched, unlike the unit tests) -- proves
        # _cdc_ts_ms round-trips end to end against real infra, not
        # just a synthetic envelope.
        assert isinstance(matching[0]["_cdc_ts_ms"], int)
        assert matching[0]["_cdc_ts_ms"] > 0

    finally:
        with postgres_connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM marketplace.carriers WHERE carrier_id = %s",
                (carrier_id,),
            )
        postgres_connection.commit()
