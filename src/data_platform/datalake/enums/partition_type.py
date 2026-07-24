from enum import StrEnum


class PartitionType(StrEnum):
    """
    Supported partitioning strategies.

    Additional strategies may be added as the platform evolves.
    """

    NONE = "none"
    DATE = "date"
    HASH = "hash"
    COLUMN = "column"