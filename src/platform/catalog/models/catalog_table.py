from dataclasses import dataclass, field

from platform.catalog.models.catalog_column import CatalogColumn
from platform.storage.models import StorageLocation


@dataclass(slots=True, frozen=True)
class CatalogTable:
    """
    Represents a catalog table.
    """

    database: str

    name: str

    location: StorageLocation

    columns: list[CatalogColumn]

    partitions: list[str] = field(default_factory=list)

    description: str | None = None