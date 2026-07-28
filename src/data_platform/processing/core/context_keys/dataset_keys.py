from enum import StrEnum, unique


@unique
class DatasetKeys(StrEnum):
    """Keys describing logical datasets."""

    DATASET = "dataset.dataset"

    DOMAIN = "dataset.domain"

    LAYER = "dataset.layer"

    FORMAT = "dataset.format"

    VERSION = "dataset.version"

    PARTITION = "dataset.partition"

    LOCATION = "dataset.location"