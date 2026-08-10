"""
Modern Data Platform

Decodes a Debezium/Kafka Connect JSON change-event envelope into a
provider-agnostic representation the Bronze Consumer can write to
Delta.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

_ZONED_TIMESTAMP = "io.debezium.time.ZonedTimestamp"
_CONNECT_DATE = "org.apache.kafka.connect.data.Date"

_EPOCH_DATE = date(1970, 1, 1)


@dataclass(frozen=True, slots=True)
class DebeziumChange:
    """
    A single decoded Debezium change event.

    ``entity`` comes from ``payload.source.table`` -- the table name
    Debezium itself recorded the change against -- rather than parsed
    out of the Kafka topic name, since the topic's naming convention
    (``marketplace.marketplace.<table>``) is this connector's config,
    not a Debezium guarantee.

    ``record`` is the row as of this change, with Debezium's JSON
    Connect logical types (``io.debezium.data.Uuid``,
    ``io.debezium.time.ZonedTimestamp``,
    ``org.apache.kafka.connect.data.Date``) already decoded into plain
    Python values (str, datetime, date). Plain scalar columns
    (string/boolean/int/double) pass through unchanged. It is ``None``
    only when neither ``after`` nor ``before`` carried data (not
    expected from this connector, since ``tombstones.on.delete`` is
    "false").

    ``op`` is Debezium's own single-character code: "r" (snapshot
    read), "c" (create), "u" (update), "d" (delete). Deciding what to
    do with each -- in particular "d", which this decoder still
    resolves to the row's last known state via ``before`` -- is a
    policy choice left to the caller, not this decoder.

    ``source_ts_ms`` is Debezium's ``payload.source.ts_ms`` -- the
    source database's own commit timestamp for this change (from the
    Postgres WAL), not ``payload.ts_ms`` (when the Debezium connector
    itself processed the event, a function of connector lag, not
    source truth). Present for every op, "r" included (Debezium's
    envelope always populates ``source.ts_ms``, structurally, not
    conditionally on op -- confirmed against the real connector, not
    assumed from the spec). ``None`` only alongside ``record is None``
    (a tombstone with neither ``after`` nor ``before`` -- there is
    nothing to timestamp).
    """

    entity: str

    op: str

    record: dict[str, Any] | None

    source_ts_ms: int | None


def decode_debezium_message(value: bytes) -> DebeziumChange:
    """
    Parses one Kafka message value produced by this project's Debezium
    connector (JsonConverter, schemas enabled -- see
    ``infrastructure/docker/docker-compose.yml``).

    Raises on anything that doesn't look like a Debezium change event
    (bad JSON, missing ``payload``/``op``/``source.table``) -- callers
    are expected to catch this per-message and skip/log rather than
    let one malformed message stop the consumer loop.
    """

    envelope = json.loads(value)

    payload = envelope["payload"]
    schema = envelope["schema"]

    op = payload["op"]
    entity = payload["source"]["table"]

    after = payload.get("after")
    before = payload.get("before")

    if after is not None:
        raw_record, field_name = after, "after"
    elif before is not None:
        raw_record, field_name = before, "before"
    else:
        return DebeziumChange(entity=entity, op=op, record=None, source_ts_ms=None)

    logical_types = _logical_types_for(schema, field_name)

    record = {
        column: _decode_value(column_value, logical_types.get(column))
        for column, column_value in raw_record.items()
    }

    # Direct access, not .get() -- source.ts_ms is a required field of
    # every real Debezium envelope (this connector's own
    # decimal.handling.mode/time.precision.mode choices don't affect
    # it), same fail-loud policy as op/source.table above. A message
    # missing it isn't a valid Debezium event -- callers already catch
    # and skip malformed messages per-message (see bronze_consumer.py).
    source_ts_ms = payload["source"]["ts_ms"]

    return DebeziumChange(
        entity=entity,
        op=op,
        record=record,
        source_ts_ms=source_ts_ms,
    )


def _logical_types_for(
    schema: dict[str, Any],
    field_name: str,
) -> dict[str, str | None]:
    """
    Maps each column name in the ``before``/``after`` struct to its
    Debezium/Connect logical type name (the struct field's ``name``
    key), or None for a plain scalar column.
    """

    for field in schema["fields"]:
        if field.get("field") == field_name and field.get("type") == "struct":
            return {
                column["field"]: column.get("name")
                for column in field["fields"]
            }

    raise ValueError(
        f"Debezium envelope schema has no '{field_name}' struct field."
    )


def _decode_value(value: Any, logical_type: str | None) -> Any:
    if value is None:
        return None

    if logical_type == _ZONED_TIMESTAMP:
        return datetime.fromisoformat(value)

    if logical_type == _CONNECT_DATE:
        return _EPOCH_DATE + timedelta(days=value)

    return value
