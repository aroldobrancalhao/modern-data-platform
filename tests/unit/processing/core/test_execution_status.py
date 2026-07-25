"""
Modern Data Platform
Processing Framework

Unit tests for ExecutionStatus.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import pytest

from data_platform.processing.core.execution_status import ExecutionStatus


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (ExecutionStatus.PENDING, False),
        (ExecutionStatus.RUNNING, False),
        (ExecutionStatus.RETRYING, False),
        (ExecutionStatus.COMPLETED, True),
        (ExecutionStatus.FAILED, True),
        (ExecutionStatus.CANCELLED, True),
        (ExecutionStatus.SKIPPED, True),
        (ExecutionStatus.TIMEOUT, True),
    ],
)
def test_is_finished(
    status: ExecutionStatus,
    expected: bool,
) -> None:
    """
    Verifies whether a status is terminal.
    """

    assert status.is_finished is expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (ExecutionStatus.COMPLETED, True),
        (ExecutionStatus.PENDING, False),
        (ExecutionStatus.RUNNING, False),
        (ExecutionStatus.FAILED, False),
        (ExecutionStatus.CANCELLED, False),
        (ExecutionStatus.SKIPPED, False),
        (ExecutionStatus.TIMEOUT, False),
        (ExecutionStatus.RETRYING, False),
    ],
)
def test_is_success(
    status: ExecutionStatus,
    expected: bool,
) -> None:
    """
    Verifies whether a status represents a successful execution.
    """

    assert status.is_success is expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (ExecutionStatus.FAILED, True),
        (ExecutionStatus.TIMEOUT, True),
        (ExecutionStatus.PENDING, False),
        (ExecutionStatus.RUNNING, False),
        (ExecutionStatus.COMPLETED, False),
        (ExecutionStatus.CANCELLED, False),
        (ExecutionStatus.SKIPPED, False),
        (ExecutionStatus.RETRYING, False),
    ],
)
def test_is_failure(
    status: ExecutionStatus,
    expected: bool,
) -> None:
    """
    Verifies whether a status represents a failed execution.
    """

    assert status.is_failure is expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (ExecutionStatus.FAILED, True),
        (ExecutionStatus.TIMEOUT, True),
        (ExecutionStatus.PENDING, False),
        (ExecutionStatus.RUNNING, False),
        (ExecutionStatus.COMPLETED, False),
        (ExecutionStatus.CANCELLED, False),
        (ExecutionStatus.SKIPPED, False),
        (ExecutionStatus.RETRYING, False),
    ],
)
def test_can_retry(
    status: ExecutionStatus,
    expected: bool,
) -> None:
    """
    Verifies whether a status allows retry.
    """

    assert status.can_retry is expected


def test_enum_values_are_stable() -> None:
    """
    Ensures enum string values remain stable.
    """

    assert ExecutionStatus.PENDING.value == "PENDING"
    assert ExecutionStatus.RUNNING.value == "RUNNING"
    assert ExecutionStatus.COMPLETED.value == "COMPLETED"
    assert ExecutionStatus.FAILED.value == "FAILED"
    assert ExecutionStatus.CANCELLED.value == "CANCELLED"
    assert ExecutionStatus.SKIPPED.value == "SKIPPED"
    assert ExecutionStatus.TIMEOUT.value == "TIMEOUT"
    assert ExecutionStatus.RETRYING.value == "RETRYING"