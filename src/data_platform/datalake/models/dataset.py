from pydantic import BaseModel, ConfigDict, Field

from data_platform.datalake.enums.compression import Compression
from data_platform.datalake.enums.encryption import Encryption
from data_platform.datalake.enums.file_format import FileFormat
from data_platform.datalake.models.partition_strategy import PartitionStrategy
from data_platform.datalake.models.retention_policy import RetentionPolicy


class Dataset(BaseModel):
    """
    Logical definition of a dataset managed by the Data Lake.

    A Dataset describes metadata and storage conventions but does not
    represent physical files stored in object storage.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    name: str = Field(
        min_length=1,
        description="Unique dataset name.",
    )

    domain: str = Field(
        min_length=1,
        description="Business domain that owns the dataset.",
    )

    description: str | None = Field(
        default=None,
        description="Optional dataset description.",
    )

    owner: str | None = Field(
        default=None,
        description="Dataset owner or responsible team.",
    )

    file_format: FileFormat = FileFormat.PARQUET

    compression: Compression = Compression.SNAPPY

    encryption: Encryption = Encryption.NONE

    retention: RetentionPolicy = Field(
        default_factory=RetentionPolicy,
    )

    partition_strategy: PartitionStrategy = Field(
        default_factory=PartitionStrategy,
    )

    tags: dict[str, str] = Field(
        default_factory=dict,
    )

    @property
    def qualified_name(self) -> str:
        """
        Fully qualified dataset name.
        """
        return f"{self.domain}.{self.name}"