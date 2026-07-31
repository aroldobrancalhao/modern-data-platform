"""
Modern Data Platform
Processing Framework

Unit tests for StorageContextWriter.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.context_writers.storage_context_writer import (
    StorageContextWriter,
)
from data_platform.processing.core.context_keys.storage_keys import (
    StorageKeys,
)
from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.storage.models import (
    StorageLocation,
    StorageMetadata,
    StorageObject,
)


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-1",
        metadata=ExecutionMetadata(execution_id="execution-1"),
    )


def create_location() -> StorageLocation:
    return StorageLocation(
        scheme="s3",
        bucket="bronze",
        key="customers/file.parquet",
    )


def test_write_populates_uri_bucket_and_object_key() -> None:
    context = create_context()

    location = create_location()

    StorageContextWriter.write(location, context)

    assert (
        context.get(StorageKeys.URI)
        == "s3://bronze/customers/file.parquet"
    )
    assert context.get(StorageKeys.BUCKET) == "bronze"
    assert (
        context.get(StorageKeys.OBJECT_KEY)
        == "customers/file.parquet"
    )


def test_write_omits_etag_when_no_storage_object_given() -> None:
    context = create_context()

    StorageContextWriter.write(create_location(), context)

    assert context.contains(StorageKeys.ETAG) is False


def test_write_omits_etag_when_metadata_is_none() -> None:
    context = create_context()

    location = create_location()

    storage_object = StorageObject(location=location, metadata=None)

    StorageContextWriter.write(
        location,
        context,
        storage_object=storage_object,
    )

    assert context.contains(StorageKeys.ETAG) is False


def test_write_populates_etag_when_metadata_available() -> None:
    context = create_context()

    location = create_location()

    storage_object = StorageObject(
        location=location,
        metadata=StorageMetadata(etag="abc123"),
    )

    StorageContextWriter.write(
        location,
        context,
        storage_object=storage_object,
    )

    assert context.get(StorageKeys.ETAG) == "abc123"


def test_write_never_sets_path_or_version() -> None:
    context = create_context()

    location = create_location()

    storage_object = StorageObject(
        location=location,
        metadata=StorageMetadata(etag="abc123"),
    )

    StorageContextWriter.write(
        location,
        context,
        storage_object=storage_object,
    )

    assert context.contains(StorageKeys.PATH) is False
    assert context.contains(StorageKeys.VERSION) is False