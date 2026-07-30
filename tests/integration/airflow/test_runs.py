import time

from data_platform.workflow.models import WorkflowStatus

MAX_WAIT_SECONDS = 20


def test_should_wait_until_run_is_finished(
    workflow_provider,
):
    run = workflow_provider.trigger(
        "platform_validation",
    )

    for _ in range(MAX_WAIT_SECONDS):

        current = workflow_provider.get_run(
            "platform_validation",
            run.run_id,
        )

        if current.status in (
            WorkflowStatus.SUCCESS,
            WorkflowStatus.FAILED,
        ):
            break

        time.sleep(1)

    assert current.status in (
        WorkflowStatus.SUCCESS,
        WorkflowStatus.FAILED,
    )