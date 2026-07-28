from enum import StrEnum, unique


@unique
class CatalogKeys(StrEnum):
    """Keys describing metadata catalog objects."""

    CATALOG = "catalog.catalog"

    DATABASE = "catalog.database"

    SCHEMA = "catalog.schema"

    TABLE = "catalog.table"

    VIEW = "catalog.view"