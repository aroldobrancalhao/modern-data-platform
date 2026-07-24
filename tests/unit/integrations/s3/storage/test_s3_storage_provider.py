from __future__ import annotations

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError

from data_platform.storage.models import StorageLocation

from integrations.aws.storage.s3_storage_provider import S3StorageProvider


@pytest.fixture
def client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def provider(client: MagicMock) -> S3StorageProvider:
    return S3StorageProvider(client)


@pytest.fixture
def location() -> StorageLocation:
    return StorageLocation(
        scheme="s3",
        bucket="bucket",
        key="folder/file.csv",
    )


def test_exists_returns_true(
    provider: S3StorageProvider,
    client: MagicMock,
    location: StorageLocation,
) -> None:

    assert provider.exists(location)

    client.head_object.assert_called_once_with(
        Bucket="bucket",
        Key="folder/file.csv",
    )


def test_exists_returns_false_when_object_does_not_exist(
    provider: S3StorageProvider,
    client: MagicMock,
    location: StorageLocation,
) -> None:

    client.head_object.side_effect = ClientError(
        {
            "Error": {
                "Code": "404",
            }
        },
        "HeadObject",
    )

    assert provider.exists(location) is False


def test_exists_reraises_unexpected_error(
    provider: S3StorageProvider,
    client: MagicMock,
    location: StorageLocation,
) -> None:

    client.head_object.side_effect = ClientError(
        {
            "Error": {
                "Code": "AccessDenied",
            }
        },
        "HeadObject",
    )

    with pytest.raises(ClientError):
        provider.exists(location)


def test_upload_from_path(
    provider: S3StorageProvider,
    client: MagicMock,
    location: StorageLocation,
) -> None:

    source = Path("/tmp/file.csv")

    provider.upload(
        location,
        source,
    )

    client.upload_file.assert_called_once_with(
        str(source),
        "bucket",
        "folder/file.csv",
    )


def test_upload_from_binary_stream(
    provider: S3StorageProvider,
    client: MagicMock,
    location: StorageLocation,
) -> None:

    stream = BytesIO(b"content")

    provider.upload(
        location,
        stream,
    )

    client.upload_fileobj.assert_called_once_with(
        stream,
        "bucket",
        "folder/file.csv",
    )


def test_download(
    provider: S3StorageProvider,
    client: MagicMock,
    location: StorageLocation,
) -> None:

    destination = Path("/tmp/download/file.csv")

    with patch("pathlib.Path.mkdir") as mkdir:

        provider.download(
            location,
            destination,
        )

        mkdir.assert_called_once_with(
            parents=True,
            exist_ok=True,
        )

    client.download_file.assert_called_once_with(
        "bucket",
        "folder/file.csv",
        str(destination),
    )


def test_delete(
    provider: S3StorageProvider,
    client: MagicMock,
    location: StorageLocation,
) -> None:

    provider.delete(location)

    client.delete_object.assert_called_once_with(
        Bucket="bucket",
        Key="folder/file.csv",
    )


def test_copy(
    provider: S3StorageProvider,
    client: MagicMock,
) -> None:

    source = StorageLocation(
        scheme="s3",
        bucket="source",
        key="input.csv",
    )

    destination = StorageLocation(
        scheme="s3",
        bucket="target",
        key="output.csv",
    )

    provider.copy(
        source,
        destination,
    )

    client.copy_object.assert_called_once_with(
        Bucket="target",
        Key="output.csv",
        CopySource={
            "Bucket": "source",
            "Key": "input.csv",
        },
    )


def test_move_calls_copy_then_delete(
    provider: S3StorageProvider,
) -> None:

    source = StorageLocation(
        scheme="s3",
        bucket="source",
        key="file.csv",
    )

    destination = StorageLocation(
        scheme="s3",
        bucket="target",
        key="file.csv",
    )

    with (
        patch.object(provider, "copy") as copy,
        patch.object(provider, "delete") as delete,
    ):

        provider.move(
            source,
            destination,
        )

        copy.assert_called_once_with(
            source,
            destination,
        )

        delete.assert_called_once_with(source)


def test_list_returns_storage_objects(
    provider: S3StorageProvider,
    client: MagicMock,
    location: StorageLocation,
) -> None:

    paginator = MagicMock()

    paginator.paginate.return_value = [
        {
            "Contents": [
                {
                    "Key": "folder/file.csv",
                    "Size": 100,
                    "ETag": '"etag"',
                    "LastModified": object(),
                }
            ]
        }
    ]

    client.get_paginator.return_value = paginator

    objects = list(provider.list(location))

    assert len(objects) == 1

    storage_object = objects[0]

    assert storage_object.location.bucket == "bucket"
    assert storage_object.location.key == "folder/file.csv"
    assert storage_object.metadata.content_length == 100
    assert storage_object.metadata.etag == "etag"


def test_list_returns_empty_when_bucket_is_empty(
    provider: S3StorageProvider,
    client: MagicMock,
    location: StorageLocation,
) -> None:

    paginator = MagicMock()

    paginator.paginate.return_value = [
        {}
    ]

    client.get_paginator.return_value = paginator

    assert list(provider.list(location)) == []


def test_head(
    provider: S3StorageProvider,
    client: MagicMock,
    location: StorageLocation,
) -> None:

    response = {
        "ContentType": "text/csv",
        "ContentLength": 100,
        "ETag": '"etag"',
        "LastModified": object(),
        "Metadata": {},
    }

    client.head_object.return_value = response

    storage_object = provider.head(location)

    assert storage_object.location == location
    assert storage_object.metadata.content_length == 100
    assert storage_object.metadata.etag == "etag"

    client.head_object.assert_called_once_with(
        Bucket="bucket",
        Key="folder/file.csv",
    )