from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.json as pajson
import pyarrow.parquet as pq

if TYPE_CHECKING:
    from .storage_provider import StorageProvider


def read_parquet(
    storage: StorageProvider,
    bucket: str,
    key: str,
) -> pa.Table:
    """
    Read a Parquet object.
    """
    with storage.open_read(bucket, key) as stream:
        return pq.read_table(stream)


def read_csv(
    storage: StorageProvider,
    bucket: str,
    key: str,
    **kwargs,
) -> pa.Table:
    """
    Read a CSV object.
    """
    with storage.open_read(bucket, key) as stream:
        return pacsv.read_csv(stream, **kwargs)


def read_json(
    storage: StorageProvider,
    bucket: str,
    key: str,
    **kwargs,
) -> pa.Table:
    """
    Read a JSON object.
    """
    with storage.open_read(bucket, key) as stream:
        return pajson.read_json(stream, **kwargs)


def read_text(
    storage: StorageProvider,
    bucket: str,
    key: str,
    encoding: str = "utf-8",
) -> str:
    """
    Read a text object.
    """
    return storage.download_bytes(
        bucket=bucket,
        key=key,
    ).decode(encoding)


def read_bytes(
    storage: StorageProvider,
    bucket: str,
    key: str,
) -> bytes:
    """
    Read binary content.
    """
    return storage.download_bytes(
        bucket=bucket,
        key=key,
    )
