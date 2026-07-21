from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlparse


@dataclass(slots=True, frozen=True)
class StorageLocation:
    """
    Represents the location of an object inside a storage provider.

    Examples:
        s3://bronze/customers/file.parquet
        gs://raw/events/data.json
        abfs://silver/orders/table.parquet
    """

    scheme: str
    bucket: str
    key: str

    def __post_init__(self) -> None:
        """
        Validates and normalizes the storage location.
        """

        scheme = self.scheme.strip().lower()
        bucket = self.bucket.strip()
        key = self.key.strip()

        if not scheme:
            raise ValueError("Storage scheme cannot be empty.")

        if not bucket:
            raise ValueError("Storage bucket cannot be empty.")

        if not key:
            raise ValueError("Storage key cannot be empty.")

        # Remove leading slash
        key = key.lstrip("/")

        # Normalize duplicated slashes
        key = PurePosixPath(key).as_posix()

        object.__setattr__(self, "scheme", scheme)
        object.__setattr__(self, "bucket", bucket)
        object.__setattr__(self, "key", key)

    @property
    def provider(self) -> str:
        """
        Returns the storage provider name.

        Example:
            s3
            gs
            abfs
        """
        return self.scheme

    @property
    def uri(self) -> str:
        """
        Returns the canonical URI.
        """
        return f"{self.scheme}://{self.bucket}/{self.key}"

    @property
    def name(self) -> str:
        """
        Returns the object filename.
        """
        return PurePosixPath(self.key).name

    @property
    def stem(self) -> str:
        """
        Returns the filename without extension.
        """
        return PurePosixPath(self.key).stem

    @property
    def suffix(self) -> str:
        """
        Returns the filename extension.
        """
        return PurePosixPath(self.key).suffix

    @property
    def parent(self) -> str:
        """
        Returns the parent directory.

        Example:

            customers/2026/
        """

        parent = PurePosixPath(self.key).parent.as_posix()

        if parent == ".":
            return ""

        return f"{parent}/"

    @classmethod
    def from_uri(cls, uri: str) -> "StorageLocation":
        """
        Creates a StorageLocation from a storage URI.

        Example:

            s3://bronze/customers/file.parquet
        """

        parsed = urlparse(uri)

        if not parsed.scheme:
            raise ValueError("Invalid storage URI: missing scheme.")

        if not parsed.netloc:
            raise ValueError("Invalid storage URI: missing bucket/container.")

        key = parsed.path.lstrip("/")

        return cls(
            scheme=parsed.scheme,
            bucket=parsed.netloc,
            key=key,
        )

    def __str__(self) -> str:
        return self.uri
