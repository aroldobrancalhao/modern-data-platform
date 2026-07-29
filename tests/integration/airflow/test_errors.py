from __future__ import annotations

import pytest

from data_platform.exceptions import (
    ResourceNotFoundError,
)


def test_should_raise_resource_not_found_when_workflow_does_not_exist(
    workflow_provider,
) -> None:
    with pytest.raises(ResourceNotFoundError):
        workflow_provider.get_workflow(
            "workflow_that_does_not_exist",
        )


def test_should_raise_resource_not_found_when_run_does_not_exist(
    workflow_provider,
) -> None:
    with pytest.raises(ResourceNotFoundError):
        workflow_provider.get_run(
            workflow_id="platform_validation",
            run_id="invalid-run-id",
        )