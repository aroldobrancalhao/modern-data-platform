"""
Modern Data Platform

Unit tests for coerce_record.

resolve_bronze_schema itself needs a real Postgres connection (it
queries information_schema.columns), so it is exercised for real by
the Bronze Consumer's real-infra test instead of a unit test here.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from decimal import Decimal

import pyarrow as pa

from data_platform.compute.bronze_schema import coerce_record

_SCHEMA = pa.schema(
    [
        ("id", pa.string()),
        ("price", pa.decimal128(10, 2)),
        ("quantity", pa.int32()),
    ]
)


def test_converts_a_double_field_to_a_decimal_matching_its_scale() -> None:
    record = {"id": "abc", "price": 19.99, "quantity": 3}

    coerced = coerce_record(record, _SCHEMA)

    assert coerced == {
        "id": "abc",
        "price": Decimal("19.99"),
        "quantity": 3,
    }


def test_rounds_a_double_field_to_its_scale_before_converting() -> None:
    record = {"id": "abc", "price": 19.999, "quantity": 1}

    coerced = coerce_record(record, _SCHEMA)

    assert coerced["price"] == Decimal("20.00")


def test_leaves_a_none_decimal_field_untouched() -> None:
    record = {"id": "abc", "price": None, "quantity": 1}

    coerced = coerce_record(record, _SCHEMA)

    assert coerced["price"] is None


def test_leaves_non_decimal_fields_untouched() -> None:
    record = {"id": "abc", "price": 19.99, "quantity": 3}

    coerced = coerce_record(record, _SCHEMA)

    assert coerced["id"] == "abc"
    assert coerced["quantity"] == 3


def test_does_not_mutate_the_original_record() -> None:
    record = {"id": "abc", "price": 19.99, "quantity": 3}

    coerce_record(record, _SCHEMA)

    assert record["price"] == 19.99
