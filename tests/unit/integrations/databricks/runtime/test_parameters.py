"""
Unit tests for get_parameter.

pyspark.dbutils.DBUtils only exists inside the Databricks Runtime's
forked PySpark distribution -- there is no real local equivalent to
test against (see the docstring on get_parameter). These tests fake
`pyspark.dbutils` in `sys.modules` instead, so the widget-reading
logic is covered fast and without a real Spark cluster.
"""

from __future__ import annotations

import sys
import types
from collections.abc import Iterator

import pytest

from integrations.databricks.runtime.parameters import get_parameter


class _FakeWidgets:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def text(self, name: str, default_value: str) -> None:
        self._values.setdefault(name, default_value)

    def get(self, name: str) -> str:
        return self._values[name]


class _FakeDBUtils:
    def __init__(self, spark: object) -> None:
        self.widgets = _FakeWidgets()


@pytest.fixture(autouse=True)
def _fake_pyspark_dbutils() -> Iterator[None]:
    fake_module = types.ModuleType("pyspark.dbutils")
    fake_module.DBUtils = _FakeDBUtils  # type: ignore[attr-defined]

    sys.modules["pyspark.dbutils"] = fake_module

    try:
        yield
    finally:
        del sys.modules["pyspark.dbutils"]


def test_returns_none_when_parameter_is_unset_and_no_default() -> None:
    assert get_parameter("entity") is None


def test_returns_the_provided_default_when_parameter_is_unset() -> None:
    assert get_parameter("entity", default="customers") == "customers"


def test_returns_the_widget_value_when_the_job_sets_the_parameter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_widgets = _FakeWidgets()
    fake_widgets._values["entity"] = "orders"

    class _PreSeededDBUtils:
        def __init__(self, spark: object) -> None:
            self.widgets = fake_widgets

    fake_module = types.ModuleType("pyspark.dbutils")
    fake_module.DBUtils = _PreSeededDBUtils  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pyspark.dbutils", fake_module)

    assert get_parameter("entity") == "orders"
