from __future__ import annotations

from data_platform.datalake.models.data_object import DataObject
from data_platform.datalake.models.datalake_location import DataLakeLocation
from data_platform.datalake.models.dataset_location import DatasetLocation
from data_platform.datalake.services.path_builder import PathBuilder


def test_dataset_path(
    dataset_location: DatasetLocation,
) -> None:

    assert (
        PathBuilder.dataset_path(
            location=dataset_location,
        )
        == "bronze/sales/orders/"
    )


def test_partition_path(
    dataset_location: DatasetLocation,
) -> None:

    assert (
        PathBuilder.partition_path(
            location=dataset_location,
            partitions={
                "year": 2026,
                "month": "07",
                "day": "24",
            },
        )
        == "bronze/sales/orders/year=2026/month=07/day=24/"
    )


def test_partition_path_without_partitions(
    dataset_location: DatasetLocation,
) -> None:

    assert (
        PathBuilder.partition_path(
            location=dataset_location,
            partitions={},
        )
        == "bronze/sales/orders/"
    )


def test_storage_location(
    datalake: DataLakeLocation,
    data_object: DataObject,
) -> None:

    location = PathBuilder.storage_location(
        datalake=datalake,
        data_object=data_object,
    )

    assert location.scheme == "s3"

    assert location.bucket == "modern-data-platform"

    assert (
        location.key
        == "bronze/sales/orders/year=2026/month=07/day=24/orders.parquet"
    )

    assert (
        location.uri
        == "s3://modern-data-platform/bronze/sales/orders/year=2026/month=07/day=24/orders.parquet"
    )