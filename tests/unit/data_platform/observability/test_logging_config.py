"""
Modern Data Platform

Unit tests for the platform CloudWatch log shipping added to
configure_logging() (Sprint 13 close-out) -- the additive
_ship_to_cloudwatch structlog processor and its LOG_CLOUDWATCH_ENABLED/
LOG_CLOUDWATCH_LOG_GROUP env-var gating. Console output via
PrintLoggerFactory is untouched by this feature and not re-tested here.

Real end-to-end delivery to the actual /mdp/dev/platform CloudWatch log
group is validated live (aws logs get-log-events), not here -- these
tests cover the module's own logic in isolation: enabled/disabled
gating, and that a shipping failure degrades to console-only instead
of crashing the caller.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import pytest

from data_platform.observability import logging_config


@pytest.fixture(autouse=True)
def _reset_module_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    _cloudwatch_logger/_cloudwatch_broken are process-lifetime globals
    by design (the whole point is "ship once, reuse the handler, stop
    retrying after the first failure") -- reset them per test so tests
    don't leak state into each other.
    """
    monkeypatch.setattr(logging_config, "_cloudwatch_logger", None)
    monkeypatch.setattr(logging_config, "_cloudwatch_broken", False)
    monkeypatch.delenv(logging_config._CLOUDWATCH_ENABLED_ENV, raising=False)
    monkeypatch.delenv(logging_config._CLOUDWATCH_LOG_GROUP_ENV, raising=False)


def test_cloudwatch_disabled_by_default_does_not_touch_the_logger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def _boom() -> None:
        nonlocal called
        called = True
        raise AssertionError("should not be reached when disabled")

    monkeypatch.setattr(logging_config, "_get_cloudwatch_logger", _boom)

    result = logging_config._ship_to_cloudwatch(None, "info", '{"event": "x"}')

    assert result == '{"event": "x"}'
    assert called is False


@pytest.mark.parametrize("value", ["1", "true", "True", "yes", "YES"])
def test_cloudwatch_enabled_env_accepts_common_truthy_spellings(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(logging_config._CLOUDWATCH_ENABLED_ENV, value)

    assert logging_config._cloudwatch_enabled() is True


@pytest.mark.parametrize("value", ["", "0", "false", "no"])
def test_cloudwatch_enabled_env_rejects_everything_else(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(logging_config._CLOUDWATCH_ENABLED_ENV, value)

    assert logging_config._cloudwatch_enabled() is False


def test_cloudwatch_enabled_ships_the_exact_rendered_line_and_returns_it_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(logging_config._CLOUDWATCH_ENABLED_ENV, "true")
    shipped: list[str] = []

    class _FakeLogger:
        def info(self, event: str) -> None:
            shipped.append(event)

    monkeypatch.setattr(
        logging_config, "_get_cloudwatch_logger", lambda: _FakeLogger()
    )

    result = logging_config._ship_to_cloudwatch(None, "info", '{"event": "real"}')

    assert result == '{"event": "real"}'
    assert shipped == ['{"event": "real"}']


def test_cloudwatch_failure_disables_shipping_for_the_rest_of_the_process_without_raising(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(logging_config._CLOUDWATCH_ENABLED_ENV, "true")
    calls = 0

    def _always_broken() -> None:
        nonlocal calls
        calls += 1
        raise RuntimeError("simulated CloudWatch/IAM failure")

    monkeypatch.setattr(logging_config, "_get_cloudwatch_logger", _always_broken)

    first = logging_config._ship_to_cloudwatch(None, "info", "line-1")
    second = logging_config._ship_to_cloudwatch(None, "info", "line-2")

    # Console output (the return value PrintLoggerFactory prints) is
    # unaffected by the shipping failure -- both lines pass through.
    assert (first, second) == ("line-1", "line-2")
    # Only the first line attempted a real ship -- _cloudwatch_broken
    # short-circuits every call after that, so the process doesn't
    # keep paying for (or warning about) a connection/IAM problem that
    # already failed once.
    assert calls == 1
    assert logging_config._cloudwatch_broken is True
    assert "CloudWatch log shipping disabled" in capsys.readouterr().err


def test_missing_log_group_raises_with_the_enabled_flag_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(logging_config._CLOUDWATCH_ENABLED_ENV, "true")
    monkeypatch.delenv(logging_config._CLOUDWATCH_LOG_GROUP_ENV, raising=False)

    with pytest.raises(RuntimeError, match=logging_config._CLOUDWATCH_LOG_GROUP_ENV):
        logging_config._get_cloudwatch_logger()


def test_configure_logging_still_configures_a_working_bound_logger() -> None:
    # Regression guard: adding _ship_to_cloudwatch to the processor
    # chain must not break the existing, already-validated console
    # pipeline -- configure_logging() should still produce a usable
    # structlog logger with no CloudWatch env vars set at all.
    logging_config.configure_logging()

    import structlog

    logger = structlog.get_logger()
    logger.info("smoke test", key="value")
