from pydantic import BaseModel, ConfigDict, Field

from data_platform.datalake.enums.partition_type import PartitionType


class PartitionStrategy(BaseModel):
    """
    Defines how a dataset should be partitioned.

    Different strategies may require different columns in the future.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    type: PartitionType = PartitionType.NONE

    columns: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Columns used for partitioning.",
    )

    @property
    def is_partitioned(self) -> bool:
        return self.type != PartitionType.NONE