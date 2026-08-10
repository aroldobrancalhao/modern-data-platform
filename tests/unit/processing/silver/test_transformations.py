"""
Real local-Spark tests for apply_standard_transformations.

Marked `spark_local`: boots a real local SparkSession (~20-30s) --
same reasoning as tests/unit/data_platform/compute/test_delta_io.py.
Run with:

    uv run pytest -m spark_local -v
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from pyspark.sql import Row, SparkSession

from data_platform.compute.spark import get_spark
from data_platform.processing.silver.transformations import (
    apply_standard_transformations,
)

pytestmark = pytest.mark.spark_local


@pytest.fixture(scope="module")
def spark() -> Iterator[SparkSession]:
    session = get_spark("silver-transformations-tests")

    try:
        yield session
    finally:
        session.stop()


def test_normalizes_column_names_to_snake_case(
    spark: SparkSession,
) -> None:
    df = spark.createDataFrame(
        [Row(**{"CustomerId": 1, "First Name": "alice"})]
    )

    result = apply_standard_transformations(df)

    assert "customer_id" in result.columns
    assert "first_name" in result.columns


def test_trims_string_columns(spark: SparkSession) -> None:
    df = spark.createDataFrame([Row(id=1, name="  alice  ")])

    result = apply_standard_transformations(df)

    row = result.first()
    assert row is not None
    assert row["name"] == "alice"


def test_removes_duplicate_records(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [Row(id=1, name="alice"), Row(id=1, name="alice")]
    )

    result = apply_standard_transformations(df)

    assert result.count() == 1


def test_adds_processed_at_and_processing_date_columns(
    spark: SparkSession,
) -> None:
    df = spark.createDataFrame([Row(id=1)])

    result = apply_standard_transformations(df)

    assert "processed_at" in result.columns
    assert "processing_date" in result.columns

    row = result.first()
    assert row is not None
    assert row["processed_at"] is not None
    assert row["processing_date"] is not None


def test_without_natural_key_columns_conflicting_rows_for_the_same_key_survive(
    spark: SparkSession,
) -> None:
    # Reproduces the real unique_dim_products_product_id bug this
    # feature resolves: two rows, same key, NOT byte-identical (differ
    # in category_id) -- dropDuplicates() alone (what
    # _remove_duplicates does) cannot tell which one is stale, so both
    # survive when natural_key_columns isn't opted into. Pins down the
    # "existing callers keep their current behavior" guarantee, not
    # just the new opt-in behavior below.
    df = spark.createDataFrame(
        [
            Row(product_id="p1", category_id="old-cat", _cdc_ts_ms=100),
            Row(product_id="p1", category_id="new-cat", _cdc_ts_ms=200),
        ]
    )

    result = apply_standard_transformations(df)

    assert result.count() == 2


def test_natural_key_columns_keeps_only_the_row_with_the_highest_order_column(
    spark: SparkSession,
) -> None:
    df = spark.createDataFrame(
        [
            Row(product_id="p1", category_id="old-cat", _cdc_ts_ms=100),
            Row(product_id="p1", category_id="new-cat", _cdc_ts_ms=200),
            Row(product_id="p2", category_id="only-cat", _cdc_ts_ms=150),
        ]
    )

    result = apply_standard_transformations(
        df, natural_key_columns=["product_id"]
    )

    rows = {row["product_id"]: row["category_id"] for row in result.collect()}

    assert result.count() == 2
    assert rows == {"p1": "new-cat", "p2": "only-cat"}


def test_natural_key_columns_respects_a_custom_order_column(
    spark: SparkSession,
) -> None:
    df = spark.createDataFrame(
        [
            Row(product_id="p1", category_id="old-cat", updated_at=100),
            Row(product_id="p1", category_id="new-cat", updated_at=200),
        ]
    )

    result = apply_standard_transformations(
        df,
        natural_key_columns=["product_id"],
        order_column="updated_at",
    )

    row = result.first()
    assert row is not None
    assert row["category_id"] == "new-cat"
