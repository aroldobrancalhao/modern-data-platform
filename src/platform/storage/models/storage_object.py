from __future__ import annotations

from dataclasses import dataclass

from platform.storage.models.storage_location import StorageLocation
from platform.storage.models.storage_metadata import StorageMetadata


@dataclass(slots=True, frozen=True)
class StorageObject:
    """
    Represents an object stored in a storage backend.
    """

    location: StorageLocation

    metadata: StorageMetadata | None = None
