"""
Modern Data Platform
Processing Framework

Shared fixtures for the processing framework's unit tests.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from data_platform.processing.runtime import execution_runtime


@pytest.fixture(autouse=True)
def _reset_stage_scoped_runtime_state() -> Iterator[None]:
    """
    Resets execution_runtime's module-level ContextVars before every
    test.

    Needed because those ContextVars are what makes stage-level
    runtime state (current stage/attempt, last result, last
    exception) safe under ParallelExecutor's concurrent stages -- each
    real asyncio.Task gets its own isolated copy (see
    execution_runtime.py's module docstring). Sync test functions
    (most of these) have no such Task boundary between them, so a
    value one test sets would otherwise leak into the next one run in
    the same process.
    """

    for var in (
        execution_runtime._current_stage,
        execution_runtime._current_attempt,
        execution_runtime._max_attempts,
        execution_runtime._stage_result,
        execution_runtime._stage_exception,
    ):
        var.set(None)

    yield
