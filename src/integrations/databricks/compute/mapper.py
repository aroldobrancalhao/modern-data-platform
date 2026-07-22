from __future__ import annotations

from databricks.sdk.service.jobs import Run
from databricks.sdk.service.jobs import RunLifeCycleState
from databricks.sdk.service.jobs import RunResultState

from data_platform.models.compute import Execution
from data_platform.models.compute import ExecutionStatus


class DatabricksComputeMapper:
    """
    Maps Databricks SDK objects into platform models.
    """

    @staticmethod
    def to_execution(
        run: Run,
    ) -> Execution:

        state = run.state

        if state is None:
            return Execution(
                execution_id=str(run.run_id),
                status=ExecutionStatus.PENDING,
            )

        lifecycle = state.life_cycle_state
        result = state.result_state

        if lifecycle in (
            RunLifeCycleState.PENDING,
            RunLifeCycleState.QUEUED,
        ):
            status = ExecutionStatus.PENDING

        elif lifecycle in (
            RunLifeCycleState.RUNNING,
            RunLifeCycleState.BLOCKED,
            RunLifeCycleState.WAITING_FOR_RETRY,
            RunLifeCycleState.TERMINATING,
        ):
            status = ExecutionStatus.RUNNING

        elif lifecycle == RunLifeCycleState.TERMINATED:

            if result == RunResultState.SUCCESS:
                status = ExecutionStatus.SUCCEEDED

            elif result == RunResultState.CANCELED:
                status = ExecutionStatus.CANCELLED

            else:
                status = ExecutionStatus.FAILED

        else:
            status = ExecutionStatus.FAILED

        return Execution(
            execution_id=str(run.run_id),
            status=status,
        )