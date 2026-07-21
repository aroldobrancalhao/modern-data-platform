from __future__ import annotations

from pathlib import Path
from typing import BinaryIO
from typing import Iterable

from botocore.exceptions import ClientError
from mypy_boto3_s3.client import S3Client

from platform.storage import StorageProvider
from platform.storage.models import StorageLocation
from platform.storage.models import StorageObject

from providers.aws.storage.error_mapper import AwsStorageErrorMapper
from providers.aws.storage.mapper import AwsStorageMapper
from platform.contracts.base_provider import BaseProvider


class S3StorageProvider(
    BaseProvider,
    StorageProvider,
):
    """
    AWS S3 implementation of StorageProvider.
    """

    def __init__(self, client: S3Client):
        self._client: S3Client = client

    def exists(
        self,
        location: StorageLocation,
    ) -> bool:
        try:
            self._client.head_object(
                Bucket=location.bucket,
                Key=location.key,
            )
            return True

        except ClientError as error:
            if AwsStorageErrorMapper.is_not_found(error):
                return False

            raise

    def upload(
        self,
        location: StorageLocation,
        source: Path | BinaryIO,
    ) -> None:

        if isinstance(source, Path):
            self._client.upload_file(
                str(source),
                location.bucket,
                location.key,
            )
            return

        self._client.upload_fileobj(
            source,
            location.bucket,
            location.key,
        )

    def download(
        self,
        location: StorageLocation,
        destination: Path,
    ) -> None:

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._client.download_file(
            location.bucket,
            location.key,
            str(destination),
        )

    def delete(
        self,
        location: StorageLocation,
    ) -> None:

        self._client.delete_object(
            Bucket=location.bucket,
            Key=location.key,
        )

    def copy(
        self,
        source: StorageLocation,
        destination: StorageLocation,
    ) -> None:

        self._client.copy_object(
            Bucket=destination.bucket,
            Key=destination.key,
            CopySource={
                "Bucket": source.bucket,
                "Key": source.key,
            },
        )

    def move(
        self,
        source: StorageLocation,
        destination: StorageLocation,
    ) -> None:

        self.copy(
            source,
            destination,
        )

        self.delete(source)

    def list(
        self,
        location: StorageLocation,
    ) -> Iterable[StorageObject]:

        paginator = self._client.get_paginator("list_objects_v2")

        for page in paginator.paginate(
            Bucket=location.bucket,
            Prefix=location.key,
        ):
            for obj in page.get("Contents", []):
                yield AwsStorageMapper.to_storage_object_summary(
                    scheme=location.scheme,
                    bucket=location.bucket,
                    response=obj,
                )

    def head(
        self,
        location: StorageLocation,
    ) -> StorageObject:

        response = self._client.head_object(
            Bucket=location.bucket,
            Key=location.key,
        )

        return AwsStorageMapper.to_storage_object(
            location,
            response,
        )