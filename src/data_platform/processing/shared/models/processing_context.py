from __future__ import annotations

from datetime import UTC
from datetime import datetime
from uuid import UUID
from uuid import uuid4

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from data_platform.datalake.models.data_object import DataObject


class ProcessingContext(BaseModel):
    """
    Represents a processing execution context.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    execution_id: UUID = Field(
        default_factory=uuid4,
    )

    data_object: DataObject

    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )