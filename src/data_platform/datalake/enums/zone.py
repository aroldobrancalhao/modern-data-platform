from enum import StrEnum


class Zone(StrEnum):
    """
    Logical Data Lake zones.

    These zones organize the lifecycle of datasets independently from
    the underlying storage technology.
    """

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"