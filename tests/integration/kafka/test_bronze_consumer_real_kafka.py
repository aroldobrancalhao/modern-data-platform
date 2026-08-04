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
_MAX_BATCH_SIZE is patched to 1 so the consumer flushes as soon as it
sees any record, instead of this test needing to wait out the real
_MAX_BATCH_AGE_SECONDS. A fresh, unique consumer group is used each
run so it always replays the topic from the earliest offset, rather
than depending on another run's committed position.

carriers is the target entity: only 5 seed rows today (no risk of
competing with the 137k+-row entities), and every one of its columns
(uuid, varchar, boolean, timestamptz) already maps cleanly in
_DATA_TYPE_TO_ARROW, so this proves the wiring without also depending
on the double-to-Decimal path (that's covered on its own by
test_bronze_schema.py's coerce_record tests).

Reuses the `real_kafka` marker, excluded from the default suite. Run
it explicitly with:

    uv run pytest tests/integration/kafka/test_bronze_consumer_real_kafka.py -m real_kafka -v

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import psycopg
import pytest
from deltalake import DeltaTable

from data_platform.bootstrap import bootstrap
from data_platform.config.settings import Settings
from data_platform.messaging.messaging_provider import MessagingProvider
from data_platform.providers.provider_factory import ProviderFactory
from data_platform.storage.config import StorageConfig

from integrations.postgres.config import PostgresSettings
from streaming.consumers import bronze_consumer
from streaming.consumers.bronze_consumer import run_bronze_consumer

pytestmark = pytest.mark.real_kafka

ENTITY = "carriers"

_MAX_POLL_ITERATIONS = 30


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
def _fast_flush(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bronze_consumer, "_MAX_BATCH_SIZE", 1)
    monkeypatch.setattr(
        bronze_consumer,
        "_CONSUMER_GROUP_ID",
        f"bronze-consumer-e2e-test-{uuid.uuid4().hex}",
    )


def test_postgres_change_flows_through_debezium_and_kafka_into_bronze(
    postgres_connection: psycopg.Connection,
    messaging_provider: MessagingProvider,
    bronze_path: Path,
) -> None:
    carrier_code = f"TEST-{uuid.uuid4().hex[:12]}"
    carrier_name = "Bronze Consumer E2E Test Carrier"

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

    finally:
        with postgres_connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM marketplace.carriers WHERE carrier_id = %s",
                (carrier_id,),
            )
        postgres_connection.commit()
