from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from uuid import uuid4

import pytest

from data_platform.datalake.enums.zone import Zone
from data_platform.datalake.models.data_object import DataObject
from data_platform.datalake.models.dataset import Dataset
from data_platform.datalake.models.dataset_location import DatasetLocation
from data_platform.processing.shared.models.processing_context import (
    ProcessingContext,
)
from data_platform.processing.shared.models.processing_result import (
    ProcessingResult,
)
from data_platform.processing.shared.models.processing_statistics import (
    ProcessingStatistics,
)


@pytest.fixture
def dataset() -> Dataset:
    return Dataset(
        name="customers",
        domain="sales",
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
        filename="customers.parquet",
        partitions={
            "year": 2026,
            "month": 7,
            "day": 24,
        },
    )


@pytest.fixture
def statistics() -> ProcessingStatistics:
    return ProcessingStatistics(
        records_read=100,
        records_written=98,
        records_failed=2,
        bytes_read=1024,
        bytes_written=980,
    )


@pytest.fixture
def processing_result(
    statistics: ProcessingStatistics,
) -> ProcessingResult:
    return ProcessingResult(
        success=True,
        duration=timedelta(seconds=5),
        statistics=statistics,
    )


@pytest.fixture
def processing_context(
    data_object: DataObject,
) -> ProcessingContext:
    return ProcessingContext(
        execution_id=uuid4(),
        data_object=data_object,
        started_at=datetime.now(UTC),
    )