from pydantic import BaseModel, ConfigDict, Field


class RetentionPolicy(BaseModel):
    """
    Defines how long a dataset should be retained.

    Retention is expressed in days. A value of 0 indicates
    that the dataset should be retained indefinitely.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    days: int = Field(
        default=0,
        ge=0,
        description="Retention period in days. Zero means infinite retention.",
    )

    @property
    def is_permanent(self) -> bool:
        """
        Indicates whether the dataset should be retained indefinitely.
        """
        return self.days == 0