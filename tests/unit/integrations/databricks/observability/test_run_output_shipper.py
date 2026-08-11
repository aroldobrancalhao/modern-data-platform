from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from integrations.databricks.observability.run_output_shipper import (
    ship_run_output_to_cloudwatch,
)


def _task(task_key: str, run_id: int) -> SimpleNamespace:
    return SimpleNamespace(
        task_key=task_key,
        run_id=run_id,
        state=SimpleNamespace(life_cycle_state="TERMINATED", result_state="SUCCESS"),
    )


def _output(**kwargs: object) -> SimpleNamespace:
    defaults = dict(
        notebook_output=None,
        logs=None,
        logs_truncated=False,
        error=None,
        error_trace=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.fixture
def fake_handler() -> MagicMock:
    with patch(
        "integrations.databricks.observability.run_output_shipper.watchtower.CloudWatchLogHandler"
    ) as handler_cls:
        instance = MagicMock()
        # A real logging.Logger compares record.levelno >= handler.level
        # when dispatching -- needs a real int, not a MagicMock attribute,
        # for the two tests below that exercise the real (non-mocked)
        # logger.info() call.
        instance.level = 0
        handler_cls.return_value = instance
        yield instance


def test_ships_one_event_per_task(fake_handler: MagicMock) -> None:
    workspace = MagicMock()
    workspace.jobs.get_run.return_value = SimpleNamespace(
        tasks=[_task("bronze", 1), _task("bronze_validate", 2), _task("silver", 3)]
    )
    workspace.jobs.get_run_output.return_value = _output(
        notebook_output=SimpleNamespace(result="7 entities processed", truncated=False)
    )

    shipped = ship_run_output_to_cloudwatch(
        workspace=workspace, run_id=999, log_group_name="/mdp/dev/databricks"
    )

    assert shipped == 3
    assert workspace.jobs.get_run_output.call_count == 3


def test_uses_the_provided_log_group_and_never_creates_it(
    fake_handler: MagicMock,
) -> None:
    workspace = MagicMock()
    workspace.jobs.get_run.return_value = SimpleNamespace(tasks=[_task("bronze", 1)])
    workspace.jobs.get_run_output.return_value = _output()

    with patch(
        "integrations.databricks.observability.run_output_shipper.watchtower.CloudWatchLogHandler"
    ) as handler_cls:
        handler_cls.return_value = fake_handler

        ship_run_output_to_cloudwatch(
            workspace=workspace, run_id=1, log_group_name="/mdp/dev/databricks"
        )

        handler_cls.assert_called_once_with(
            log_group_name="/mdp/dev/databricks", create_log_group=False
        )


def test_closes_the_handler_even_when_get_run_output_raises(
    fake_handler: MagicMock,
) -> None:
    workspace = MagicMock()
    workspace.jobs.get_run.return_value = SimpleNamespace(tasks=[_task("bronze", 1)])
    workspace.jobs.get_run_output.side_effect = RuntimeError("API error")

    with pytest.raises(RuntimeError):
        ship_run_output_to_cloudwatch(
            workspace=workspace, run_id=1, log_group_name="/mdp/dev/databricks"
        )

    fake_handler.close.assert_called_once()


def test_raises_instead_of_silently_shipping_zero_events_for_a_run_with_no_tasks(
    fake_handler: MagicMock,
) -> None:
    workspace = MagicMock()
    workspace.jobs.get_run.return_value = SimpleNamespace(tasks=[])

    with pytest.raises(ValueError, match="no task runs to ship"):
        ship_run_output_to_cloudwatch(
            workspace=workspace, run_id=1, log_group_name="/mdp/dev/databricks"
        )


def test_message_includes_notebook_result_and_task_identity(
    fake_handler: MagicMock,
) -> None:
    workspace = MagicMock()
    workspace.jobs.get_run.return_value = SimpleNamespace(
        tasks=[_task("silver", 42)]
    )
    workspace.jobs.get_run_output.return_value = _output(
        notebook_output=SimpleNamespace(result="137207 rows", truncated=False),
        logs="print output here",
    )

    logged_lines: list[str] = []

    def _capture_info(message: str) -> None:
        logged_lines.append(message)

    with patch(
        "integrations.databricks.observability.run_output_shipper.logging.getLogger"
    ) as get_logger:
        logger = MagicMock()
        logger.info.side_effect = _capture_info
        get_logger.return_value = logger

        ship_run_output_to_cloudwatch(
            workspace=workspace, run_id=999, log_group_name="/mdp/dev/databricks"
        )

    assert len(logged_lines) == 1
    line = logged_lines[0]
    assert "task_key=silver" in line
    assert "task_run_id=42" in line
    assert "notebook_result=137207 rows" in line
    assert "logs=print output here" in line


def test_error_and_error_trace_included_on_failure(fake_handler: MagicMock) -> None:
    workspace = MagicMock()
    workspace.jobs.get_run.return_value = SimpleNamespace(tasks=[_task("bronze", 1)])
    workspace.jobs.get_run_output.return_value = _output(
        error="NameError: x is not defined",
        error_trace="Traceback ...",
    )

    logged_lines: list[str] = []

    with patch(
        "integrations.databricks.observability.run_output_shipper.logging.getLogger"
    ) as get_logger:
        logger = MagicMock()
        logger.info.side_effect = logged_lines.append
        get_logger.return_value = logger

        ship_run_output_to_cloudwatch(
            workspace=workspace, run_id=1, log_group_name="/mdp/dev/databricks"
        )

    assert "error=NameError: x is not defined" in logged_lines[0]
    assert "error_trace=Traceback ..." in logged_lines[0]
