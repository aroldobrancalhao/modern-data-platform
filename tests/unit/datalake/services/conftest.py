from __future__ import annotations

from unittest.mock import Mock

import pytest

from data_platform.datalake.enums.zone import Zone
from data_platform.datalake.models.data_object import DataObject
from data_platform.datalake.models.datalake_location import DataLakeLocation
from data_platform.datalake.models.dataset import Dataset
from data_platform.datalake.models.dataset_location import DatasetLocation
from data_platform.datalake.services.datalake_service import DataLakeService


@pytest.fixture
def dataset() -> Dataset:
    return Dataset(
        domain="sales",
        name="orders",
    )


@pytest.fixture
def dataset_location(
    dataset: Dataset,
) -> DatasetLocation:
    return DatasetLocation(
        zone=Zone.BRONZE,
        dataset=dataset,
    )


@pytest.fixture
def data_object(
    dataset_location: DatasetLocation,
) -> DataObject:
    return DataObject(
        location=dataset_location,
        filename="orders.parquet",
        partitions={
            "year": 2026,
            "month": "07",
            "day": "24",
        },
    )


@pytest.fixture
def datalake() -> DataLakeLocation:
    return DataLakeLocation(
        scheme="s3",
        bucket="modern-data-platform",
    )


@pytest.fixture
def storage_provider() -> Mock:
    return Mock()


@pytest.fixture
def datalake_service(
    storage_provider: Mock,
    datalake: DataLakeLocation,
) -> DataLakeService:
    return DataLakeService(
        storage_provider=storage_provider,
        datalake=datalake,
    )