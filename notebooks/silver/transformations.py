import re

from typing import Optional

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, trim
from pyspark.sql.types import StringType
from pyspark.sql.functions import current_date, current_timestamp


def apply_standard_transformations(df: DataFrame) -> DataFrame:
    """
    Apply all standard Silver transformations.
    """
    df = _normalize_column_names(df)
    df = _trim_string_columns(df)
    df = _remove_duplicates(df)
    df = _add_metadata(df)

    return df


def _normalize_column_names(df: DataFrame) -> DataFrame:
    """
    Normalize DataFrame column names to snake_case.
    """

    def normalize(column_name: str) -> str:
        # CamelCase/PascalCase -> snake_case
        column_name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", column_name)

        # Substitui separadores por "_"
        column_name = re.sub(r"[.\-/\s]+", "_", column_name)

        # Remove caracteres especiais
        column_name = re.sub(r"[^a-zA-Z0-9_]", "", column_name)

        # Remove múltiplos "_"
        column_name = re.sub(r"_+", "_", column_name)

        # Remove "_" do início/fim
        column_name = column_name.strip("_")

        return column_name.lower()

    return df.toDF(*(normalize(column) for column in df.columns))


def _trim_string_columns(df: DataFrame) -> DataFrame:
    """
    Trim leading and trailing whitespace from all string columns.
    """
    for field in df.schema.fields:
        if isinstance(field.dataType, StringType):
            df = df.withColumn(field.name, trim(col(field.name)))

    return df


def _remove_duplicates(
    df: DataFrame,
    subset: Optional[list[str]] = None,
) -> DataFrame:
    """
    Remove duplicate records.

    If a subset of columns is provided, duplicates are identified
    using only those columns. Otherwise, all columns are considered.
    """
    if subset:
        return df.dropDuplicates(subset)

    return df.dropDuplicates()


def _add_metadata(df: DataFrame) -> DataFrame:
    """
    Add standard metadata columns.
    """
    return df.withColumn("processed_at", current_timestamp()).withColumn(
        "processing_date", current_date()
    )
