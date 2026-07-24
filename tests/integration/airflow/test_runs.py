import time

from data_platform.workflow.models import WorkflowStatus


def test_should_wait_until_run_is_finished(
    workflow_provider,
):
    run = workflow_provider.trigger(
        "platform_validation",
    )

    for _ in range(20):

        current = workflow_provider.get_run(
            "platform_validation",
            run.id,
        )

        if current.status in (
            "success",
            "failed",
        ):
            break

        time.sleep(1)

    assert current.status in (
        WorkflowStatus.SUCCESS,
        WorkflowStatus.FAILED,
    )