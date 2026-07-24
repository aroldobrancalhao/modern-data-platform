from unittest.mock import MagicMock

from data_platform.models.compute import Execution
from data_platform.models.compute import ExecutionStatus
from data_platform.models.compute import Workload
from integrations.databricks.compute.databricks_compute_provider import (
    DatabricksComputeProvider,
)


def test_should_execute_workload() -> None:
    client = MagicMock()

    run = MagicMock(
        run_id=1,
        state=MagicMock(),
    )

    client.run.return_value = run

    provider = DatabricksComputeProvider(
        client,
    )

    workload = Workload(
        identifier="daily-sales",
    )

    execution = provider.execute(
        workload,
    )

    assert isinstance(
        execution,
        Execution,
    )

    assert execution.execution_id == "1"

    assert execution.status in ExecutionStatus

    client.run.assert_called_once_with(
        workload,
    )