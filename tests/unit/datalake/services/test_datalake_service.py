from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from data_platform.datalake.models.data_object import DataObject
from data_platform.datalake.services.datalake_service import DataLakeService
from data_platform.storage.models import StorageLocation


def test_location(
    datalake_service: DataLakeService,
    data_object: DataObject,
) -> None:

    location = datalake_service.location(
        object=data_object,
    )

    assert (
        location.uri
        == "s3://modern-data-platform/bronze/sales/orders/year=2026/month=07/day=24/orders.parquet"
    )


def test_exists(
    datalake_service: DataLakeService,
    storage_provider: Mock,
    data_object: DataObject,
) -> None:

    storage_provider.exists.return_value = True

    assert datalake_service.exists(
        object=data_object,
    )

    storage_provider.exists.assert_called_once()


def test_upload(
    datalake_service: DataLakeService,
    storage_provider: Mock,
    data_object: DataObject,
) -> None:

    datalake_service.upload(
        object=data_object,
        source=Path("orders.parquet"),
    )

    storage_provider.upload.assert_called_once()


def test_download(
    datalake_service: DataLakeService,
    storage_provider: Mock,
    data_object: DataObject,
) -> None:

    datalake_service.download(
        object=data_object,
        destination=Path("orders.parquet"),
    )

    storage_provider.download.assert_called_once()


def test_delete(
    datalake_service: DataLakeService,
    storage_provider: Mock,
    data_object: DataObject,
) -> None:

    datalake_service.delete(
        object=data_object,
    )

    storage_provider.delete.assert_called_once()


def test_head(
    datalake_service: DataLakeService,
    storage_provider: Mock,
    data_object: DataObject,
) -> None:

    datalake_service.head(
        object=data_object,
    )

    storage_provider.head.assert_called_once()


def test_list(
    datalake_service: DataLakeService,
    storage_provider: Mock,
    data_object: DataObject,
) -> None:

    datalake_service.list(
        object=data_object,
    )

    storage_provider.list.assert_called_once()


def test_copy(
    datalake_service: DataLakeService,
    storage_provider: Mock,
) -> None:

    source = StorageLocation(
        scheme="s3",
        bucket="bucket",
        key="source.parquet",
    )

    destination = StorageLocation(
        scheme="s3",
        bucket="bucket",
        key="destination.parquet",
    )

    datalake_service.copy(
        source=source,
        destination=destination,
    )

    storage_provider.copy.assert_called_once_with(
        source=source,
        destination=destination,
    )


def test_move(
    datalake_service: DataLakeService,
    storage_provider: Mock,
) -> None:

    source = StorageLocation(
        scheme="s3",
        bucket="bucket",
        key="source.parquet",
    )

    destination = StorageLocation(
        scheme="s3",
        bucket="bucket",
        key="destination.parquet",
    )

    datalake_service.move(
        source=source,
        destination=destination,
    )

    storage_provider.move.assert_called_once_with(
        source=source,
        destination=destination,
    )