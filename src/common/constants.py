from enum import StrEnum


class Layer(StrEnum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class FileFormat(StrEnum):
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"
    DELTA = "delta"


class SaveMode(StrEnum):
    OVERWRITE = "overwrite"
    APPEND = "append"
    IGNORE = "ignore"
    ERROR = "error"
