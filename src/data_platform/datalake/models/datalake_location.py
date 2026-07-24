from pydantic import BaseModel, ConfigDict, Field


class DataLakeLocation(BaseModel):
    """
    Represents the physical location of the Data Lake.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    scheme: str = Field(
        min_length=1,
    )

    bucket: str = Field(
        min_length=1,
    )