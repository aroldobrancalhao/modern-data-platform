"""
Modern Data Platform

Bronze Consumer: the streaming half of ADR-0008's flow --

    PostgreSQL -> Debezium -> Kafka -> Bronze Consumer -> BronzeService

-- landing Debezium change events straight into the same Bronze Delta
tables the batch flow writes (``bronze/{entity}/``), via the pure-
Python ``deltalake`` package rather than Spark. This is a deliberate
PoC-scope divergence from ``data_platform.compute.delta_io.write_delta``
(Spark-based, batch-only): pulling Spark into a long-running streaming
process for this project would cost far more than it proves.

Known limitations, accepted for this phase (see project-decisions.md):

- No Dead Letter Queue and no sophisticated retry. A message that
  fails to decode is logged and dropped -- it does not block its
  topic, but it is also not recovered automatically. A micro-batch
  that fails to write to Delta is retried on the next cycle (offsets
  are only committed after a successful write), with no backoff.
- No distributed lock against the batch flow writing the same Delta
  tables concurrently. Accepted as low risk: the Databricks full_pipeline
  Job Bundle has no schedule, so batch only ever runs on a manual
  trigger.
- Deletes are not applied as deletes. Per DebeziumChange's contract,
  a "d" op still carries the row's last known state (via ``before``),
  which this consumer simply appends like any other change -- Bronze
  keeps every version of a row it has ever seen, deleted or not.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import pyarrow as pa
from deltalake import write_deltalake

from data_platform.compute.bronze_schema import coerce_record, resolve_bronze_schema
from data_platform.messaging.messaging_provider import MessagingProvider
from data_platform.monitoring.logger import get_logger
from data_platform.storage.config import StorageConfig

from integrations.kafka.messaging.debezium_envelope import decode_debezium_message

logger = get_logger(__name__)

_TOPIC_PREFIX = "marketplace.marketplace."

_CONSUMER_GROUP_ID = "bronze-consumer"

_MAX_BATCH_SIZE = 100

_MAX_BATCH_AGE_SECONDS = 30.0

_POLL_TIMEOUT_SECONDS = 1.0

STREAMING_ENTITIES: tuple[str, ...] = (
    "carriers",
    "categories",
    "customer_addresses",
    "customers",
    "inventories",
    "inventory_movements",
    "order_items",
    "order_status_history",
    "orders",
    "payment_methods",
    "payments",
    "products",
    "reviews",
    "sellers",
    "shipments",
    "warehouses",
)
"""
Mirrors the Debezium connector's ``table.include.list``
(``infrastructure/docker/debezium/connectors/marketplace-postgres.json``),
minus ``refunds``: the ``refunds`` table is empty in Postgres today and
``snapshot.mode: initial`` only creates a topic once a table's first
change event fires, so there is no ``refunds`` topic yet to subscribe
to. Refunds is also explicitly a "Future modules" entity in
project-decisions.md.
"""


def topic_for(entity: str) -> str:
    return f"{_TOPIC_PREFIX}{entity}"


@dataclass(slots=True)
class _EntityBuffer:
    records: list[dict[str, Any]] = field(default_factory=list)

    opened_at: float | None = None

    def add(self, record: dict[str, Any]) -> None:
        if self.opened_at is None:
            self.opened_at = time.monotonic()

        self.records.append(record)

    def is_due(self, now: float) -> bool:
        if not self.records:
            return False

        if len(self.records) >= _MAX_BATCH_SIZE:
            return True

        return (
            self.opened_at is not None
            and (now - self.opened_at) >= _MAX_BATCH_AGE_SECONDS
        )

    def clear(self) -> None:
        self.records = []
        self.opened_at = None


def run_bronze_consumer(
    provider: MessagingProvider,
    *,
    entities: Sequence[str] = STREAMING_ENTITIES,
    max_iterations: int | None = None,
) -> None:
    """
    Consumes every topic in ``entities`` in a round-robin poll loop,
    micro-batching each entity's records (``_MAX_BATCH_SIZE`` messages
    or ``_MAX_BATCH_AGE_SECONDS``, whichever comes first) before
    writing them to that entity's Bronze Delta table and committing
    the consumed offsets.

    ``max_iterations`` bounds the number of round-robin cycles across
    all topics -- ``None`` (the default) runs forever, which is what
    the production entrypoint (``scripts/run_bronze_consumer.py``)
    wants; tests pass a small integer instead so the loop terminates
    on its own.
    """

    schemas = {entity: resolve_bronze_schema(entity) for entity in entities}

    buffers = {entity: _EntityBuffer() for entity in entities}

    iterations = 0

    while max_iterations is None or iterations < max_iterations:

        for entity in entities:
            topic = topic_for(entity)

            message = provider.consume(
                topic,
                group_id=_CONSUMER_GROUP_ID,
                timeout_seconds=_POLL_TIMEOUT_SECONDS,
                auto_commit=False,
            )

            if message is not None:
                _buffer_message(entity, topic, message.value, buffers[entity])

            buffer = buffers[entity]

            if buffer.is_due(time.monotonic()):
                _flush(
                    provider,
                    entity=entity,
                    topic=topic,
                    buffer=buffer,
                    schema=schemas[entity],
                )

        iterations += 1


def _buffer_message(
    entity: str,
    topic: str,
    value: bytes,
    buffer: _EntityBuffer,
) -> None:
    try:
        change = decode_debezium_message(value)
    except Exception:
        logger.exception(
            "Skipping malformed Debezium message on topic '%s'.", topic
        )
        return

    if change.record is not None:
        buffer.add(change.record)


def _flush(
    provider: MessagingProvider,
    *,
    entity: str,
    topic: str,
    buffer: _EntityBuffer,
    schema: pa.Schema,
) -> None:
    try:
        table = pa.Table.from_pylist(
            [coerce_record(record, schema) for record in buffer.records],
            schema=schema,
        )

        write_deltalake(StorageConfig.bronze(entity), table, mode="append")
    except Exception:
        logger.exception(
            "Bronze write failed for entity '%s' (%d buffered records) -- "
            "offsets left uncommitted, will retry next cycle.",
            entity,
            len(buffer.records),
        )
        return

    provider.commit(topic, group_id=_CONSUMER_GROUP_ID)

    buffer.clear()

    logger.info(
        "Wrote %d record(s) to Bronze for entity '%s'.",
        len(table),
        entity,
    )
