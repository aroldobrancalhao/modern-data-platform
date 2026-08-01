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
