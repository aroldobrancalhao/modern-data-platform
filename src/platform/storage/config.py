from __future__ import annotations

from pydantic import BaseModel


class StorageSettings(BaseModel):
    """
    Common storage configuration.
    """

    provider: str = "local"

    default_bucket: str = "default"

    create_bucket_if_missing: bool = True

    overwrite: bool = True
