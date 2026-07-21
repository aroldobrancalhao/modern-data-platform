from dataclasses import dataclass

from platform.storage.models import StorageLocation


@dataclass(slots=True, frozen=True)
class CatalogDatabase:
    """
    Represents a logical database/schema.
    """

    name: str

    location: StorageLocation | None = None

    description: str | None = None