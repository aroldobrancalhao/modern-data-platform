import re

from typing import Optional

from pyspark.sql import DataFrame, Window
from pyspark.sql.functions import col, row_number, trim
from pyspark.sql.types import StringType
from pyspark.sql.functions import current_date, current_timestamp


def apply_standard_transformations(
    df: DataFrame,
    *,
    natural_key_columns: Optional[list[str]] = None,
    order_column: str = "cdc_ts_ms",
) -> DataFrame:
    """
    Apply all standard Silver transformations.

    ``natural_key_columns`` (default ``None``, so every existing
    caller -- today, only the batch flow via ``bronze_batch()`` --
    keeps its current behavior unchanged) opts into a second, CDC-aware
    dedup pass (``_deduplicate_by_key``) beyond ``_remove_duplicates``'s
    exact-row check: keeps only the most recent row per natural key,
    ordered by ``order_column``. Exists for whenever an entity is built
    from streaming Bronze (``.bronze()``) instead of the batch snapshot
    (``.bronze_batch()``) -- no real caller passes this yet (see
    docs/architecture/roadmap-next-steps.md), so this is exercised
    directly by this module's own unit tests rather than an end-to-end
    pipeline test.

    ``order_column`` defaults to ``"cdc_ts_ms"``, not
    ``"_cdc_ts_ms"`` (the column's actual name in Bronze -- see
    ``bronze_schema.resolve_bronze_schema``'s ``include_cdc_metadata``)
    -- found live while adding this feature's own tests:
    ``_normalize_column_names`` (the *first* step this function runs)
    strips leading underscores from every column, unconditionally, so
    by the time ``_deduplicate_by_key`` runs, the column genuinely is
    named ``cdc_ts_ms``. Passing the Bronze name here fails with an
    unresolved-column error, not a silent no-op.

    Resolves the same class of bug found investigating a real
    ``unique_dim_products_product_id`` Silver test failure: an
    entity's business ``updated_at`` column can change at the source
    without that column itself being bumped, so ordering by a business
    timestamp isn't reliable for deciding which of several conflicting
    rows for the same key is actually the latest -- ordering by CDC
    provenance (the source database's own commit time) is.
    """
    df = _normalize_column_names(df)
    df = _trim_string_columns(df)
    df = _remove_duplicates(df)

    if natural_key_columns:
        df = _deduplicate_by_key(df, natural_key_columns, order_column)

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


def _deduplicate_by_key(
    df: DataFrame,
    key_columns: list[str],
    order_column: str,
) -> DataFrame:
    """
    Keeps only the most recent row per ``key_columns`` (a natural key,
    e.g. ``["product_id"]``), ordered by ``order_column`` descending.

    Unlike ``_remove_duplicates`` (which only drops byte-identical
    rows), this resolves *conflicting* rows for the same key that
    differ in some other column -- the case ``dropDuplicates()``
    cannot catch, since the rows genuinely aren't identical.
    """
    window = Window.partitionBy(*key_columns).orderBy(col(order_column).desc())

    return (
        df.withColumn("_dedup_rank", row_number().over(window))
        .filter(col("_dedup_rank") == 1)
        .drop("_dedup_rank")
    )


def _add_metadata(df: DataFrame) -> DataFrame:
    """
    Add standard metadata columns.
    """
    return df.withColumn("processed_at", current_timestamp()).withColumn(
        "processing_date", current_date()
    )
