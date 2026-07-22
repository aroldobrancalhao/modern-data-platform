from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import PropertyMock
from unittest.mock import patch

import pytest

from providers.databricks.core.databricks_context import DatabricksContext


def test_should_resolve_existing_job() -> None:
    context = DatabricksContext()

    with patch.object(
        DatabricksContext,
        "jobs",
        new_callable=PropertyMock,
        return_value={"daily-sales": 123},
    ):
        assert context.resolve_job("daily-sales") == 123


def test_should_raise_when_job_does_not_exist() -> None:
    context = DatabricksContext()

    with patch.object(
        DatabricksContext,
        "jobs",
        new_callable=PropertyMock,
        return_value={},
    ):
        with pytest.raises(ValueError):
            context.resolve_job("missing-job")


def test_should_cache_jobs() -> None:
    workspace = MagicMock()

    workspace.jobs.list.return_value = [
        SimpleNamespace(
            job_id=1,
            settings=SimpleNamespace(
                name="daily-sales",
            ),
        ),
    ]

    context = DatabricksContext()

    with patch.object(
        DatabricksContext,
        "workspace",
        new_callable=PropertyMock,
        return_value=workspace,
    ):
        first = context.jobs
        second = context.jobs

        assert first is second

        workspace.jobs.list.assert_called_once()