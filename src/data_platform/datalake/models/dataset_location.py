from pydantic import BaseModel, ConfigDict

from data_platform.datalake.enums.zone import Zone
from data_platform.datalake.models.dataset import Dataset


class DatasetLocation(BaseModel):
    """
    Represents the logical location of a dataset inside the Data Lake.

    This model is storage-agnostic and contains only logical information
    required to identify where a dataset belongs.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    zone: Zone

    dataset: Dataset