from __future__ import annotations

from pyspark.sql import SparkSession


def get_parameter(
    name: str,
    default: str | None = None,
) -> str | None:
    """
    Retrieves a Databricks notebook/Job parameter via dbutils.widgets.

    ``pyspark.dbutils.DBUtils`` only exists inside the Databricks
    Runtime's forked PySpark distribution -- it is not part of the
    open-source PySpark package, so this can only actually run on a
    real Databricks cluster. There is no local/offline equivalent to
    exercise the real thing against; the unit test for this module
    fakes ``pyspark.dbutils`` in ``sys.modules`` instead of skipping
    coverage entirely.

    ``default=None`` means "no fallback" -- an unset widget returns
    None instead of an empty string. Passing an explicit default
    seeds the widget with that value, so the returned value is never
    None in that case.
    """
    from pyspark.dbutils import DBUtils  # type: ignore[import-not-found]

    spark = SparkSession.getActiveSession()

    dbutils = DBUtils(spark)

    dbutils.widgets.text(name, default if default is not None else "")

    value = dbutils.widgets.get(name)

    if value == "" and default is None:
        return None

    return value
