"""
Modern Data Platform
Processing Framework

Unit tests for ValueObject.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from typing import Any, cast

from dataclasses import FrozenInstanceError
from dataclasses import dataclass

import pytest

from data_platform.processing.core.value_object import ValueObject


@dataclass(
    frozen=True,
    eq=False,
    slots=True,
)
class FakeValueObject(ValueObject):
    """
    Fake ValueObject used for unit testing.
    """

    name: str
    age: int


def test_value_objects_with_same_values_are_equal() -> None:
    """
    Value objects with identical values
    must be equal.
    """

    left = FakeValueObject(
        name="Alice",
        age=30,
    )

    right = FakeValueObject(
        name="Alice",
        age=30,
    )

    assert left == right


def test_value_objects_with_different_values_are_not_equal() -> None:
    """
    Value objects with different values
    must not be equal.
    """

    left = FakeValueObject(
        name="Alice",
        age=30,
    )

    right = FakeValueObject(
        name="Bob",
        age=30,
    )

    assert left != right


def test_equal_value_objects_have_same_hash() -> None:
    """
    Equal value objects must generate
    identical hash values.
    """

    left = FakeValueObject(
        name="Alice",
        age=30,
    )

    right = FakeValueObject(
        name="Alice",
        age=30,
    )

    assert hash(left) == hash(right)


def test_different_value_objects_have_different_hashes() -> None:
    """
    Different value objects should
    produce different hash values.
    """

    left = FakeValueObject(
        name="Alice",
        age=30,
    )

    right = FakeValueObject(
        name="Alice",
        age=31,
    )

    assert hash(left) != hash(right)


def test_value_object_is_immutable() -> None:
    """
    Value objects must be immutable.
    """

    value = FakeValueObject(
        name="Alice",
        age=30,
    )

    with pytest.raises(FrozenInstanceError):
        cast(Any, value).age = 31


def test_value_object_is_not_equal_to_other_type() -> None:
    """
    Comparison with unrelated objects
    must return False.
    """

    value = FakeValueObject(
        name="Alice",
        age=30,
    )

    assert value != "Alice"


def test_repr_contains_field_values() -> None:
    """
    The representation should contain
    every field value.
    """

    value = FakeValueObject(
        name="Alice",
        age=30,
    )

    assert (
        repr(value)
        == "FakeValueObject(name='Alice', age=30)"
    )