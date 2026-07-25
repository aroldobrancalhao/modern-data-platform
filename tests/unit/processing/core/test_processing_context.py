"""
Modern Data Platform
Processing Framework

Unit tests for ProcessingContext.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

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

    context.set("customer_id", 123)

    assert context.get("customer_id") == 123


def test_get_returns_default_when_key_does_not_exist() -> None:
    """
    Missing keys should return the supplied default.
    """

    context = create_context()

    assert context.get("missing") is None
    assert context.get("missing", "default") == "default"


def test_contains_returns_true_for_existing_key() -> None:
    """
    contains() should detect stored keys.
    """

    context = create_context()

    context.set("key", "value")

    assert context.contains("key") is True


def test_contains_returns_false_for_missing_key() -> None:
    """
    contains() should return False for unknown keys.
    """

    context = create_context()

    assert context.contains("missing") is False


def test_remove_existing_key() -> None:
    """
    remove() should delete an existing key.
    """

    context = create_context()

    context.set("key", "value")

    context.remove("key")

    assert context.contains("key") is False
    assert context.values == {}


def test_remove_missing_key_does_not_raise() -> None:
    """
    Removing a missing key should be a no-op.
    """

    context = create_context()

    context.remove("missing")

    assert context.values == {}


def test_clear_removes_all_values() -> None:
    """
    clear() should remove every stored value.
    """

    context = create_context()

    context.set("a", 1)
    context.set("b", 2)

    context.clear()

    assert context.values == {}


def test_values_returns_copy() -> None:
    """
    values property must return a defensive copy.
    """

    context = create_context()

    context.set("name", "Alice")

    values = context.values

    values["name"] = "Bob"

    assert context.get("name") == "Alice"


def test_set_overwrites_existing_value() -> None:
    """
    Setting the same key twice should replace the value.
    """

    context = create_context()

    context.set("key", "old")
    context.set("key", "new")

    assert context.get("key") == "new"