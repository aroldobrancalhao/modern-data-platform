from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.json as pajson
import pyarrow.parquet as pq

if TYPE_CHECKING:
    from .storage_provider import StorageProvider


def write_parquet(
    storage: StorageProvider,
    table: pa.Table,
    bucket: str,
    key: str,
    **kwargs,
) -> None:
    """
    Write a Parquet object.
    """
    with storage.open_write(bucket, key) as stream:
        pq.write_table(table, stream, **kwargs)


def write_csv(
    storage: StorageProvider,
    table: pa.Table,
    bucket: str,
    key: str,
    **kwargs,
) -> None:
    """
    Write a CSV object.
    """
    with storage.open_write(bucket, key) as stream:
        pacsv.write_csv(table, stream, **kwargs)


def write_json(
    storage: StorageProvider,
    table: pa.Table,
    bucket: str,
    key: str,
) -> None:
    """
    Write newline-delimited JSON (NDJSON).
    """
    with storage.open_write(bucket, key) as stream:
        pajson.write_json(table, stream)


def write_text(
    storage: StorageProvider,
    content: str,
    bucket: str,
    key: str,
    encoding: str = "utf-8",
) -> None:
    """
    Write text.
    """
    storage.upload_bytes(
        bucket=bucket,
        key=key,
        data=content.encode(encoding),
    )


def write_bytes(
    storage: StorageProvider,
    content: bytes,
    bucket: str,
    key: str,
) -> None:
    """
    Write binary content.
    """
    storage.upload_bytes(
        bucket=bucket,
        key=key,
        data=content,
    )
