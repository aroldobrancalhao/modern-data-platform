"""
Syntax-only lint for the notebooks rewritten in N3.

A real Databricks notebook run is not possible locally (dbutils only
exists on a Databricks cluster -- see
integrations.databricks.runtime.parameters). This does not execute
anything; it parses each .ipynb's code cells with `ast.parse` to catch
obvious syntax errors (e.g. a leftover common.* typo, unbalanced
parens) before the notebook ever reaches a real Job.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

NOTEBOOKS = (
    REPO_ROOT / "notebooks/bronze/ingest_sources.ipynb",
    REPO_ROOT / "notebooks/bronze/optimize_bronze.ipynb",
    REPO_ROOT / "notebooks/bronze/validate_bronze.ipynb",
    REPO_ROOT / "notebooks/silver/transform_silver.ipynb",
)


def _strip_magics(source: str) -> str:
    """
    Drops IPython line magics (e.g. ``%pip install ...``) -- valid in
    a real notebook kernel, not valid Python syntax on their own, so
    `ast.parse` would reject them. This is a syntax lint, not an
    executor: skipping the magic line is enough to still catch a
    genuine typo/syntax error in the rest of the cell.
    """
    return "\n".join(
        line
        for line in source.splitlines()
        if not line.lstrip().startswith("%")
    )


def _code_cells(notebook_path: Path) -> list[str]:
    notebook = json.loads(notebook_path.read_text())

    return [
        _strip_magics("".join(cell["source"]))
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    ]


@pytest.mark.parametrize(
    "notebook_path",
    NOTEBOOKS,
    ids=lambda path: path.name,
)
def test_every_code_cell_has_valid_python_syntax(
    notebook_path: Path,
) -> None:
    for index, source in enumerate(_code_cells(notebook_path)):
        try:
            ast.parse(source)
        except SyntaxError as error:
            pytest.fail(f"{notebook_path.name} cell {index}: {error}")
