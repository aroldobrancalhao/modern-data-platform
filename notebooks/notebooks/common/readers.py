from pyspark.sql import DataFrame
from pyspark.sql import SparkSession

from common.constants import FileFormat


def read_dataset(
    spark: SparkSession,
    path: str,
    file_format: FileFormat = FileFormat.DELTA,
) -> DataFrame:

    return (
        spark.read
        .format(file_format.value)
        .load(path)
    )


def read_csv(
    spark: SparkSession,
    path: str,
    header: bool = True,
    infer_schema: bool = True,
) -> DataFrame:

    return (
        spark.read
        .option("header", header)
        .option("inferSchema", infer_schema)
        .csv(path)
    )