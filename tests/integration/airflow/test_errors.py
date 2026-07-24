import pytest


def test_should_raise_when_workflow_does_not_exist(
    workflow_provider,
):
    with pytest.raises(Exception):
        workflow_provider.get_workflow(
            "workflow_that_does_not_exist",
        )


def test_should_raise_when_run_does_not_exist(
    workflow_provider,
):
    with pytest.raises(Exception):
        workflow_provider.get_run(
            workflow_id="platform_validation",
            run_id="invalid-run-id",
        )