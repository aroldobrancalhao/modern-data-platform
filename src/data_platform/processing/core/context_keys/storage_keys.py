from enum import StrEnum, unique


@unique
class StorageKeys(StrEnum):
    """Keys describing persisted data."""

    URI = "storage.uri"

    PATH = "storage.path"

    BUCKET = "storage.bucket"

    OBJECT_KEY = "storage.object_key"

    VERSION = "storage.version"

    ETAG = "storage.etag"