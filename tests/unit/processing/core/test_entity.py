"""
Modern Data Platform
Processing Framework

Unit tests for Entity.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass

from data_platform.processing.core.entity import Entity


@dataclass(eq=False, slots=True)
class FakeEntity(Entity[str]):
    """
    Fake entity used for unit testing.
    """


@dataclass(eq=False, slots=True)
class AnotherFakeEntity(Entity[str]):
    """
    Another fake entity used to validate
    entity type comparisons.
    """


def test_entities_with_same_type_and_id_are_equal() -> None:
    """
    Entities with the same type and identifier
    must be considered equal.
    """

    left = FakeEntity(id="entity-1")
    right = FakeEntity(id="entity-1")

    assert left == right


def test_entities_with_different_ids_are_not_equal() -> None:
    """
    Entities with different identifiers
    must not be equal.
    """

    left = FakeEntity(id="entity-1")
    right = FakeEntity(id="entity-2")

    assert left != right


def test_entities_with_same_id_but_different_types_are_not_equal() -> None:
    """
    Equality must also consider the entity type.
    """

    left = FakeEntity(id="entity-1")
    right = AnotherFakeEntity(id="entity-1")

    assert left != right


def test_entity_is_not_equal_to_non_entity_object() -> None:
    """
    Entity comparisons with unrelated objects
    must return False.
    """

    entity = FakeEntity(id="entity-1")

    assert entity != "entity-1"


def test_equal_entities_have_same_hash() -> None:
    """
    Equal entities must generate the same hash.
    """

    left = FakeEntity(id="entity-1")
    right = FakeEntity(id="entity-1")

    assert hash(left) == hash(right)


def test_different_entities_have_different_hashes() -> None:
    """
    Different entities should produce
    different hashes.
    """

    left = FakeEntity(id="entity-1")
    right = FakeEntity(id="entity-2")

    assert hash(left) != hash(right)


def test_repr_contains_class_name_and_identifier() -> None:
    """
    The string representation should include
    the class name and identifier.
    """

    entity = FakeEntity(id="entity-1")

    assert repr(entity) == "FakeEntity(id='entity-1')"