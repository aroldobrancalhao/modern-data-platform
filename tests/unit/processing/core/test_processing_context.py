"""
Modern Data Platform
Processing Framework

Unit tests for ProcessingContext.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.core.context_keys.execution_keys import (
    ExecutionKeys,
)
from data_platform.processing.core.context_keys.processing_keys import (
    ProcessingKeys,
)
from data_platform.processing.core.execution_metadata import ExecutionMetadata
from data_platform.processing.core.processing_context import ProcessingContext


def create_context() -> ProcessingContext:
    """
    Creates a ProcessingContext for testing.
    """

    return ProcessingContext(
        id="context-1",
        metadata=ExecutionMetadata(
            execution_id="execution-1",
        ),
    )


def test_create_processing_context() -> None:
    """
    Should create a processing context.
    """

    context = create_context()

    assert context.id == "context-1"
    assert context.metadata.execution_id == "execution-1"
    assert context.values == {}


def test_set_and_get_value() -> None:
    """
    Should store and retrieve values.
    """

    context = create_context()

    context.set(ProcessingKeys.INPUT, 123)

    assert context.get(ProcessingKeys.INPUT) == 123


def test_get_returns_default_when_key_does_not_exist() -> None:
    """
    Missing keys should return the supplied default.
    """

    context = create_context()

    assert context.get(ProcessingKeys.INPUT) is None
    assert context.get(ProcessingKeys.INPUT, "default") == "default"


def test_contains_returns_true_for_existing_key() -> None:
    """
    contains() should detect stored keys.
    """

    context = create_context()

    context.set(ProcessingKeys.INPUT, "value")

    assert context.contains(ProcessingKeys.INPUT) is True


def test_contains_returns_false_for_missing_key() -> None:
    """
    contains() should return False for unknown keys.
    """

    context = create_context()

    assert context.contains(ProcessingKeys.INPUT) is False


def test_remove_existing_key() -> None:
    """
    remove() should delete an existing key.
    """

    context = create_context()

    context.set(ProcessingKeys.INPUT, "value")

    context.remove(ProcessingKeys.INPUT)

    assert context.contains(ProcessingKeys.INPUT) is False
    assert context.values == {}


def test_remove_missing_key_does_not_raise() -> None:
    """
    Removing a missing key should be a no-op.
    """

    context = create_context()

    context.remove(ProcessingKeys.INPUT)

    assert context.values == {}


def test_clear_removes_all_values() -> None:
    """
    clear() should remove every stored value.
    """

    context = create_context()

    context.set(ProcessingKeys.INPUT, 1)
    context.set(ProcessingKeys.OUTPUT, 2)

    context.clear()

    assert context.values == {}


def test_values_returns_copy() -> None:
    """
    values property must return a defensive copy.
    """

    context = create_context()

    context.set(ExecutionKeys.STATUS, "Alice")

    values = context.values

    values[ExecutionKeys.STATUS.value] = "Bob"

    assert context.get(ExecutionKeys.STATUS) == "Alice"


def test_set_overwrites_existing_value() -> None:
    """
    Setting the same key twice should replace the value.
    """

    context = create_context()

    context.set(ProcessingKeys.INPUT, "old")
    context.set(ProcessingKeys.INPUT, "new")

    assert context.get(ProcessingKeys.INPUT) == "new"
