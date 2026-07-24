from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from data_platform.datalake.models.data_object import DataObject
from data_platform.processing.shared.models.processing_context import (
    ProcessingContext,
)


def test_processing_context(
    processing_context: ProcessingContext,
    data_object: DataObject,
) -> None:
    assert isinstance(processing_context.execution_id, UUID)
    assert isinstance(processing_context.started_at, datetime)
    assert processing_context.data_object == data_object


def test_model_is_frozen(
    processing_context: ProcessingContext,
) -> None:
    with pytest.raises(ValidationError):
        processing_context.execution_id = UUID(int=0)


def test_extra_fields_are_forbidden(
    data_object: DataObject,
) -> None:
    with pytest.raises(ValidationError):
        ProcessingContext.model_validate(
            {
                "data_object": data_object,
                "extra_field": True,
            }
        )