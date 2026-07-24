from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from data_platform.models.compute import Workload
from integrations.databricks.compute.client import DatabricksClient


def test_should_execute_job() -> None:
    context = MagicMock()

    context.resolve_job.return_value = 100

    waiter = MagicMock()

    waiter.result.return_value = SimpleNamespace(
        run_id=999,
    )

    run = SimpleNamespace(
        run_id=999,
    )

    context.workspace.jobs.run_now.return_value = waiter

    context.workspace.jobs.get_run.return_value = run

    client = DatabricksClient(context)

    workload = Workload(
        identifier="daily-sales",
    )

    result = client.run(workload)

    assert result == run

    context.workspace.jobs.run_now.assert_called_once()

    context.workspace.jobs.get_run.assert_called_once_with(
        run_id=999,
    )


def test_should_raise_when_run_id_is_none() -> None:
    context = MagicMock()

    context.resolve_job.return_value = 100

    waiter = MagicMock()

    waiter.result.return_value = SimpleNamespace(
        run_id=None,
    )

    context.workspace.jobs.run_now.return_value = waiter

    client = DatabricksClient(context)

    workload = Workload(
        identifier="daily-sales",
    )

    with pytest.raises(RuntimeError):
        client.run(workload)