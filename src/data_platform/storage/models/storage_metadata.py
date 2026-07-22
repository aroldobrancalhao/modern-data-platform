from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class StorageMetadata:
    """
    Metadata associated with a storage object.
    """

    content_type: str | None = None

    content_length: int | None = None

    etag: str | None = None

    last_modified: datetime | None = None

    metadata: dict[str, str] | None = None
