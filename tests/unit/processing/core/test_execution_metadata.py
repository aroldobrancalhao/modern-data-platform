"""
Modern Data Platform
Processing Framework

Unit tests for ExecutionMetadata.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from typing import Any, cast

from dataclasses import FrozenInstanceError
from datetime import datetime
from types import MappingProxyType

import pytest

from data_platform.processing.core.execution_metadata import ExecutionMetadata


def test_create_execution_metadata_with_required_fields() -> None:
    """
    Should create metadata using only required fields.
    """

    metadata = ExecutionMetadata(
        execution_id="execution-1",
    )

    assert metadata.execution_id == "execution-1"
    assert metadata.pipeline_id is None
    assert metadata.stage_id is None
    assert metadata.correlation_id is None
    assert metadata.parent_execution_id is None
    assert metadata.started_at is None
    assert metadata.attributes == {}


def test_create_execution_metadata_with_all_fields() -> None:
    """
    Should preserve all supplied values.
    """

    started_at = datetime.now()

    metadata = ExecutionMetadata(
        execution_id="execution-1",
        pipeline_id="pipeline-1",
        stage_id="stage-1",
        correlation_id="corr-1",
        parent_execution_id="parent-1",
        started_at=started_at,
        attributes=MappingProxyType(
            {
                "env": "dev",
            }
        ),
    )

    assert metadata.execution_id == "execution-1"
    assert metadata.pipeline_id == "pipeline-1"
    assert metadata.stage_id == "stage-1"
    assert metadata.correlation_id == "corr-1"
    assert metadata.parent_execution_id == "parent-1"
    assert metadata.started_at == started_at
    assert metadata.attributes["env"] == "dev"


def test_metadata_is_immutable() -> None:
    """
    ExecutionMetadata must be immutable.
    """

    metadata = ExecutionMetadata(
        execution_id="execution-1",
    )

    with pytest.raises(FrozenInstanceError):
        cast(Any, metadata).execution_id = "execution-2"


def test_attributes_mapping_is_read_only() -> None:
    """
    Attributes must expose a read-only mapping.
    """

    metadata = ExecutionMetadata(
        execution_id="execution-1",
    )

    with pytest.raises(TypeError):
        cast(Any, metadata.attributes)["env"] = "prod"


def test_with_attribute_returns_new_instance() -> None:
    """
    with_attribute() should return a new immutable object.
    """

    metadata = ExecutionMetadata(
        execution_id="execution-1",
    )

    updated = metadata.with_attribute(
        "env",
        "dev",
    )

    assert updated is not metadata
    assert updated.attributes["env"] == "dev"
    assert metadata.attributes == {}


def test_with_attribute_preserves_existing_values() -> None:
    """
    with_attribute() must preserve all existing fields.
    """

    started_at = datetime.now()

    metadata = ExecutionMetadata(
        execution_id="execution-1",
        pipeline_id="pipeline-1",
        stage_id="stage-1",
        correlation_id="corr-1",
        parent_execution_id="parent-1",
        started_at=started_at,
    )

    updated = metadata.with_attribute(
        "key",
        "value",
    )

    assert updated.execution_id == metadata.execution_id
    assert updated.pipeline_id == metadata.pipeline_id
    assert updated.stage_id == metadata.stage_id
    assert updated.correlation_id == metadata.correlation_id
    assert updated.parent_execution_id == metadata.parent_execution_id
    assert updated.started_at == metadata.started_at


def test_with_attribute_keeps_previous_attributes() -> None:
    """
    Existing attributes should remain available.
    """

    metadata = ExecutionMetadata(
        execution_id="execution-1",
        attributes=MappingProxyType(
            {
                "env": "dev",
            }
        ),
    )

    updated = metadata.with_attribute(
        "version",
        "1.0",
    )

    assert updated.attributes == {
        "env": "dev",
        "version": "1.0",
    }


def test_with_attribute_overwrites_existing_key() -> None:
    """
    Existing keys should be replaced.
    """

    metadata = ExecutionMetadata(
        execution_id="execution-1",
        attributes=MappingProxyType(
            {
                "env": "dev",
            }
        ),
    )

    updated = metadata.with_attribute(
        "env",
        "prod",
    )

    assert updated.attributes["env"] == "prod"