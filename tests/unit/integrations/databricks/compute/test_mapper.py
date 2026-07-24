from databricks.sdk.service.jobs import Run
from databricks.sdk.service.jobs import RunLifeCycleState
from databricks.sdk.service.jobs import RunResultState
from databricks.sdk.service.jobs import RunState

from data_platform.models.compute import ExecutionStatus
from integrations.databricks.compute.mapper import DatabricksComputeMapper


def make_run(
    lifecycle,
    result=None,
):
    return Run(
        run_id=1,
        state=RunState(
            life_cycle_state=lifecycle,
            result_state=result,
        ),
    )


def test_pending() -> None:
    execution = DatabricksComputeMapper.to_execution(
        make_run(
            RunLifeCycleState.PENDING,
        ),
    )

    assert execution.status == ExecutionStatus.PENDING


def test_running() -> None:
    execution = DatabricksComputeMapper.to_execution(
        make_run(
            RunLifeCycleState.RUNNING,
        ),
    )

    assert execution.status == ExecutionStatus.RUNNING


def test_success() -> None:
    execution = DatabricksComputeMapper.to_execution(
        make_run(
            RunLifeCycleState.TERMINATED,
            RunResultState.SUCCESS,
        ),
    )

    assert execution.status == ExecutionStatus.SUCCEEDED


def test_cancelled() -> None:
    execution = DatabricksComputeMapper.to_execution(
        make_run(
            RunLifeCycleState.TERMINATED,
            RunResultState.CANCELED,
        ),
    )

    assert execution.status == ExecutionStatus.CANCELLED


def test_failed() -> None:
    execution = DatabricksComputeMapper.to_execution(
        make_run(
            RunLifeCycleState.TERMINATED,
            RunResultState.FAILED,
        ),
    )

    assert execution.status == ExecutionStatus.FAILED