"""
Real local-Spark tests for delta_io.

Marked `spark_local`: boots a real local SparkSession (~20-30s) to
exercise read_raw/read_delta/write_delta against the filesystem
(pytest's tmp_path) for real -- no mocks, no external infra, just
excluded from the default suite because of the boot cost. Run with:

    uv run pytest -m spark_local -v

IMPORTANT (WSL memory): this local environment's docker compose stack
(Kafka, Airflow, Postgres, Debezium) already uses most of the WSL's
~7.7GB RAM. Running these tests with that stack up has triggered the
OOM killer against the Spark JVM (`Out of memory: Killed process
(java)`, confirmed via `dmesg`). Stop the stack first:

    docker compose -f infrastructure/docker/docker-compose.yml stop

...then run `-m spark_local`, and start the stack again afterwards.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from pyspark.sql import Row, SparkSession

from data_platform.compute.delta_io import read_delta, read_raw, write_delta
from data_platform.compute.spark import get_spark

pytestmark = pytest.mark.spark_local


@pytest.fixture(scope="module")
def spark() -> Iterator[SparkSession]:
    session = get_spark("delta-io-tests")

    try:
        yield session
    finally:
        session.stop()


def test_write_delta_and_read_delta_round_trip(
    spark: SparkSession,
    tmp_path: Path,
) -> None:
    path = str(tmp_path / "delta_table")

    df = spark.createDataFrame(
        [Row(id=1, name="alice"), Row(id=2, name="bob")]
    )

    write_delta(df, path)

    result = read_delta(spark, path)

    assert sorted(
        (row.asDict() for row in result.collect()),
        key=lambda row: row["id"],
    ) == sorted(
        (row.asDict() for row in df.collect()),
        key=lambda row: row["id"],
    )


def test_write_delta_overwrite_mode_replaces_existing_data(
    spark: SparkSession,
    tmp_path: Path,
) -> None:
    path = str(tmp_path / "delta_table_overwrite")

    write_delta(
        spark.createDataFrame([Row(id=1)]),
        path,
    )

    write_delta(
        spark.createDataFrame([Row(id=2)]),
        path,
        mode="overwrite",
    )

    result = read_delta(spark, path)

    assert [row.id for row in result.collect()] == [2]


def test_read_raw_reads_plain_parquet_written_outside_delta(
    spark: SparkSession,
    tmp_path: Path,
) -> None:
    path = str(tmp_path / "raw_customers")

    df = spark.createDataFrame([Row(id=1), Row(id=2), Row(id=3)])

    df.write.parquet(path)

    result = read_raw(spark, path)

    assert result.count() == 3
