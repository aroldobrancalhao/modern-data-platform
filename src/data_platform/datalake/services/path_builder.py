from __future__ import annotations

from data_platform.datalake.models.data_object import DataObject
from data_platform.datalake.models.datalake_location import DataLakeLocation
from data_platform.datalake.models.dataset_location import DatasetLocation
from data_platform.storage.models import StorageLocation


class PathBuilder:
    """
    Builds logical paths and storage locations for datasets
    inside the Data Lake.

    This class is storage agnostic and is responsible only
    for generating standardized paths.
    """

    @staticmethod
    def dataset_path(
        *,
        location: DatasetLocation,
    ) -> str:
        """
        Returns the base path of a dataset.

        Example:
            bronze/sales/orders/
        """

        return (
            f"{location.zone.value}/"
            f"{location.dataset.domain}/"
            f"{location.dataset.name}/"
        )

    @staticmethod
    def partition_path(
        *,
        location: DatasetLocation,
        partitions: dict[str, str | int],
    ) -> str:
        """
        Returns the dataset path including partition folders.

        Example:
            bronze/sales/orders/year=2026/month=07/day=24/
        """

        base = PathBuilder.dataset_path(
            location=location,
        )

        if not partitions:
            return base

        partition_path = "/".join(
            f"{key}={value}"
            for key, value in partitions.items()
        )

        return f"{base}{partition_path}/"

    @staticmethod
    def storage_location(
        *,
        datalake: DataLakeLocation,
        data_object: DataObject,
    ) -> StorageLocation:
        """
        Builds a StorageLocation for a logical Data Lake object.
        """

        key = PathBuilder.partition_path(
            location=data_object.location,
            partitions=data_object.partitions,
        )

        key = f"{key}{data_object.filename}"

        return StorageLocation(
            scheme=datalake.scheme,
            bucket=datalake.bucket,
            key=key,
        )