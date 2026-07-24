from enum import StrEnum


class Compression(StrEnum):
    """
    Supported compression algorithms for datasets.

    PARQUET datasets should normally use SNAPPY.
    """

    NONE = "none"
    SNAPPY = "snappy"
    GZIP = "gzip"
    ZSTD = "zstd"