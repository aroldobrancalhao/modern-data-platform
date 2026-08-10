"""
Modern Data Platform

Unit tests for decode_debezium_message.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import pytest

from integrations.kafka.messaging.debezium_envelope import (
    DebeziumChange,
    decode_debezium_message,
)


_SOURCE_TS_MS = 1785607968684


def _envelope(
    *,
    op: str,
    table: str = "orders",
    after: dict[str, Any] | None = None,
    before: dict[str, Any] | None = None,
    logical_types: dict[str, str] | None = None,
    source_ts_ms: int = _SOURCE_TS_MS,
) -> bytes:
    logical_types = logical_types or {}

    fields = [
        {"field": name, "name": logical_types.get(name)}
        for name in (after or before or {})
    ]

    payload: dict[str, Any] = {
        "op": op,
        "source": {"table": table, "ts_ms": source_ts_ms},
    }

    if after is not None:
        payload["after"] = after

    if before is not None:
        payload["before"] = before

    envelope = {
        "schema": {
            "fields": [
                {
                    "field": "after" if after is not None else "before",
                    "type": "struct",
                    "fields": fields,
                }
            ]
        },
        "payload": payload,
    }

    return json.dumps(envelope).encode("utf-8")


def test_decodes_a_create_event_with_plain_scalar_columns() -> None:
    message = _envelope(
        op="c",
        table="orders",
        after={"id": "abc-123", "total": 42.5, "is_paid": True},
    )

    change = decode_debezium_message(message)

    assert change == DebeziumChange(
        entity="orders",
        op="c",
        record={"id": "abc-123", "total": 42.5, "is_paid": True},
        source_ts_ms=_SOURCE_TS_MS,
    )


def test_decodes_a_zoned_timestamp_column() -> None:
    message = _envelope(
        op="u",
        after={"updated_at": "2026-08-04T12:30:00Z"},
        logical_types={"updated_at": "io.debezium.time.ZonedTimestamp"},
    )

    change = decode_debezium_message(message)

    assert change.record == {
        "updated_at": datetime.fromisoformat("2026-08-04T12:30:00Z")
    }


def test_decodes_a_connect_date_column_as_days_since_epoch() -> None:
    message = _envelope(
        op="c",
        after={"birth_date": 19584},
        logical_types={"birth_date": "org.apache.kafka.connect.data.Date"},
    )

    change = decode_debezium_message(message)

    assert change.record == {"birth_date": date(2023, 8, 15)}


def test_delete_event_falls_back_to_the_before_state() -> None:
    message = _envelope(
        op="d",
        before={"id": "abc-123", "total": 42.5},
        after=None,
    )

    change = decode_debezium_message(message)

    assert change.op == "d"
    assert change.record == {"id": "abc-123", "total": 42.5}
    assert change.source_ts_ms == _SOURCE_TS_MS


def test_snapshot_read_event_is_decoded_like_a_create_event() -> None:
    # "r" (snapshot read) carries data via `after`, same shape as "c" --
    # confirmed live against this project's own Debezium connector
    # (Frente 3/CDC provenance investigation) that no op-based
    # branching exists anywhere in the real decode/buffer path, so a
    # forced re-snapshot (snapshot.mode) decodes no differently than
    # ordinary inserts. This test pins that down structurally too, not
    # just by reading the source.
    message = _envelope(
        op="r",
        after={"id": "abc-123", "total": 42.5},
    )

    change = decode_debezium_message(message)

    assert change == DebeziumChange(
        entity="orders",
        op="r",
        record={"id": "abc-123", "total": 42.5},
        source_ts_ms=_SOURCE_TS_MS,
    )


def test_neither_after_nor_before_yields_a_none_record() -> None:
    envelope = {
        "schema": {"fields": []},
        "payload": {"op": "t", "source": {"table": "orders"}},
    }

    change = decode_debezium_message(json.dumps(envelope).encode("utf-8"))

    assert change == DebeziumChange(
        entity="orders", op="t", record=None, source_ts_ms=None
    )


def test_null_column_value_passes_through_as_none() -> None:
    message = _envelope(
        op="c",
        after={"cancelled_at": None},
        logical_types={"cancelled_at": "io.debezium.time.ZonedTimestamp"},
    )

    change = decode_debezium_message(message)

    assert change.record == {"cancelled_at": None}


def test_raises_when_the_envelope_has_no_payload() -> None:
    with pytest.raises(KeyError):
        decode_debezium_message(json.dumps({"schema": {}}).encode("utf-8"))
