from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from data_platform.datalake.models.dataset_location import DatasetLocation


class DataObject(BaseModel):
    """
    Represents a logical object stored inside a dataset.

    This model contains all information required to locate
    an object inside the Data Lake independently of the
    underlying storage provider.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    location: DatasetLocation

    filename: str = Field(
        min_length=1,
        description="Object filename.",
    )

    partitions: dict[str, str | int] = Field(
        default_factory=dict,
        description="Partition values.",
    )