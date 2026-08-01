from pyspark.sql import DataFrame, SparkSession


def read_delta(spark: SparkSession, path: str) -> DataFrame:
    return spark.read.format("delta").load(path)


def write_delta(
    df: DataFrame,
    path: str,
    mode: str = "overwrite",
) -> None:
    df.write.format("delta").mode(mode).save(path)


def read_raw(spark: SparkSession, path: str) -> DataFrame:
    """
    Reads the raw landing files a PostgresExtractionStage produced
    (``raw/{entity}/``) -- plain Parquet, not yet a Delta table. The
    Delta conversion happens downstream, when the Bronze layer first
    writes this data with ``write_delta``.
    """
    return spark.read.parquet(path)
