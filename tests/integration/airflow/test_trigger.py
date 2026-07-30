from data_platform.workflow.models import WorkflowStatus


def test_should_trigger_with_empty_payload(
    workflow_provider,
):
    run = workflow_provider.trigger(
        workflow_id="platform_validation",
    )

    assert run.run_id
    assert run.workflow_id == "platform_validation"

    assert run.status in (
        WorkflowStatus.PENDING,
        WorkflowStatus.RUNNING,
    )


def test_should_trigger_with_parameters(
    workflow_provider,
):
    run = workflow_provider.trigger(
        workflow_id="platform_validation",
        parameters={
            "environment": "integration",
            "batch": 1,
        },
    )

    assert run.run_id
    assert run.workflow_id == "platform_validation"

    assert run.status in (
        WorkflowStatus.PENDING,
        WorkflowStatus.RUNNING,
    )

    assert run.parameters["environment"] == "integration"
    assert run.parameters["batch"] == 1