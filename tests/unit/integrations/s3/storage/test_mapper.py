from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from data_platform.storage.models import StorageLocation

from integrations.aws.storage.mapper import AwsStorageMapper


def test_to_storage_metadata() -> None:

    response = {
        "ContentType": "application/json",
        "ContentLength": 1024,
        "ETag": '"abc123"',
        "LastModified": datetime(
            2026,
            1,
            1,
            tzinfo=ZoneInfo("UTC"),
        ),
        "Metadata": {
            "source": "tests",
        },
    }

    metadata = AwsStorageMapper.to_storage_metadata(response)

    assert metadata.content_type == "application/json"
    assert metadata.content_length == 1024
    assert metadata.etag == "abc123"
    assert metadata.metadata == {
        "source": "tests",
    }


def test_to_storage_metadata_without_metadata() -> None:

    response = {
        "ContentLength": 10,
        "ETag": '"etag"',
        "LastModified": datetime.now(
            tz=ZoneInfo("UTC"),
        ),
    }

    metadata = AwsStorageMapper.to_storage_metadata(response)

    assert metadata.metadata == {}
    assert metadata.content_type is None


def test_to_storage_object() -> None:

    location = StorageLocation(
        scheme="s3",
        bucket="bucket",
        key="folder/file.csv",
    )

    response = {
        "ContentType": "text/csv",
        "ContentLength": 20,
        "ETag": '"etag"',
        "LastModified": datetime.now(
            tz=ZoneInfo("UTC"),
        ),
        "Metadata": {},
    }

    storage_object = AwsStorageMapper.to_storage_object(
        location,
        response,
    )

    assert storage_object.location == location
    assert storage_object.metadata.content_length == 20
    assert storage_object.metadata.etag == "etag"


def test_to_storage_object_summary() -> None:

    response = {
        "Key": "folder/file.csv",
        "Size": 2048,
        "ETag": '"summary"',
        "LastModified": datetime.now(
            tz=ZoneInfo("UTC"),
        ),
    }

    storage_object = AwsStorageMapper.to_storage_object_summary(
        scheme="s3",
        bucket="bucket",
        response=response,
    )

    assert storage_object.location.scheme == "s3"
    assert storage_object.location.bucket == "bucket"
    assert storage_object.location.key == "folder/file.csv"

    assert storage_object.metadata.content_type is None
    assert storage_object.metadata.content_length == 2048
    assert storage_object.metadata.etag == "summary"
    assert storage_object.metadata.metadata == {}