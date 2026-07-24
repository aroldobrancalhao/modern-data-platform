from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class ProcessingStatistics(BaseModel):
    """
    Statistics collected during a processing execution.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    records_read: int = Field(
        default=0,
        ge=0,
    )

    records_written: int = Field(
        default=0,
        ge=0,
    )

    records_failed: int = Field(
        default=0,
        ge=0,
    )

    bytes_read: int = Field(
        default=0,
        ge=0,
    )

    bytes_written: int = Field(
        default=0,
        ge=0,
    )