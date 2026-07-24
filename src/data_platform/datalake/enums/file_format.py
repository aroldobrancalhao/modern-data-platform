from enum import StrEnum


class FileFormat(StrEnum):
    """
    Supported physical file formats for datasets stored in the Data Lake.

    The initial implementation uses PARQUET as the default format.
    Additional formats (e.g. DELTA, AVRO, JSON, CSV) will be introduced
    as the platform evolves.
    """

    PARQUET = "parquet"
    DELTA = "delta"
    CSV = "csv"
    JSON = "json"
    AVRO = "avro"