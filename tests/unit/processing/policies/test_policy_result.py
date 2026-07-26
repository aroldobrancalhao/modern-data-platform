"""
Modern Data Platform
Processing Framework

Unit tests for PolicyResult.
"""

import pytest

from data_platform.processing.policies.policy_result import (
    PolicyResult,
)


def test_should_create_default_policy_result() -> None:

    result = PolicyResult()

    assert result.continue_execution is True
    assert result.retry is False
    assert result.cancel_pipeline is False
    assert result.reason is None


def test_should_create_retry_result() -> None:

    result = PolicyResult(
        retry=True,
    )

    assert result.retry is True
    assert result.continue_execution is True
    assert result.cancel_pipeline is False


def test_should_create_cancel_result() -> None:

    result = PolicyResult(
        continue_execution=False,
        cancel_pipeline=True,
    )

    assert result.continue_execution is False
    assert result.cancel_pipeline is True
    assert result.retry is False


def test_should_be_hashable() -> None:

    result = PolicyResult()

    assert hash(result)


def test_should_raise_when_cancel_and_continue() -> None:

    with pytest.raises(ValueError):
        PolicyResult(
            continue_execution=True,
            cancel_pipeline=True,
        )


def test_should_raise_when_cancel_and_retry() -> None:

    with pytest.raises(ValueError):
        PolicyResult(
            continue_execution=False,
            retry=True,
            cancel_pipeline=True,
        )


def test_should_raise_when_retry_without_continue() -> None:

    with pytest.raises(ValueError):
        PolicyResult(
            continue_execution=False,
            retry=True,
        )