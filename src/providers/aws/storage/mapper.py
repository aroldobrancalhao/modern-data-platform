from __future__ import annotations

from typing import Any

from platform.storage.models import StorageLocation
from platform.storage.models import StorageMetadata
from platform.storage.models import StorageObject


class AwsStorageMapper:
    """
    Maps AWS S3 responses to storage domain models.
    """

    @staticmethod
    def to_storage_metadata(
        response: dict[str, Any],
    ) -> StorageMetadata:

        return StorageMetadata(
            content_type=response.get("ContentType"),
            content_length=response["ContentLength"],
            etag=response["ETag"].strip('"'),
            last_modified=response["LastModified"],
            metadata=response.get("Metadata", {}),
        )

    @staticmethod
    def to_storage_object(
        location: StorageLocation,
        response: dict[str, Any],
    ) -> StorageObject:

        return StorageObject(
            location=location,
            metadata=AwsStorageMapper.to_storage_metadata(response),
        )

    @staticmethod
    def to_storage_object_summary(
        scheme: str,
        bucket: str,
        response: dict[str, Any],
    ) -> StorageObject:

        location = StorageLocation(
            scheme=scheme,
            bucket=bucket,
            key=response["Key"],
        )

        metadata = StorageMetadata(
            content_type=None,
            content_length=response["Size"],
            etag=response["ETag"].strip('"'),
            last_modified=response["LastModified"],
            metadata={},
        )

        return StorageObject(
            location=location,
            metadata=metadata,
        )
