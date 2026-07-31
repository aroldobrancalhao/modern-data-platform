"""
Modern Data Platform
Processing Framework

Publishes StorageProvider results into the ProcessingContext.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.processing.core.context_keys.storage_keys import (
    StorageKeys,
)
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.storage.models import StorageLocation, StorageObject


class StorageContextWriter:
    """
    Translates a StorageLocation (and, when available, the
    StorageMetadata describing it) into StorageKeys and publishes them
    into the ProcessingContext.

    This class knows about StorageLocation/StorageObject (provider-
    agnostic domain models) and about ProcessingContext/StorageKeys. It
    does not know about any concrete StorageProvider (S3, GCS, ADLS,
    ...) -- the caller is responsible for obtaining the location/object
    from a Provider and passing it here.

    StorageKeys.URI, BUCKET and OBJECT_KEY are always populated, since
    StorageLocation always carries them. StorageKeys.ETAG is populated
    only when metadata is available (e.g. after ``provider.head(...)``
    or ``provider.list(...)``; not after ``provider.upload(...)``,
    which returns no metadata today).

    StorageKeys.PATH and VERSION are intentionally left unset: the
    current storage model does not distinguish a filesystem-style
    "path" from OBJECT_KEY, nor a "version" from ETAG, for the S3
    provider implemented so far.
    """

    @staticmethod
    def write(
        location: StorageLocation,
        context: ProcessingContext,
        *,
        storage_object: StorageObject | None = None,
    ) -> None:
        """
        Publishes a StorageLocation into the ProcessingContext.

        Parameters
        ----------
        location:
            The location that was written/read (e.g. the argument
            passed to ``provider.upload(location, ...)``, or
            ``storage_object.location`` after ``provider.head(...)``).

        context:
            The ProcessingContext of the current execution.

        storage_object:
            The StorageObject returned by the Provider, when available
            (e.g. from ``provider.head(...)``). Used only to read
            ``metadata.etag``, when present.
        """

        context.set(
            StorageKeys.URI,
            location.uri,
        )

        context.set(
            StorageKeys.BUCKET,
            location.bucket,
        )

        context.set(
            StorageKeys.OBJECT_KEY,
            location.key,
        )

        if storage_object is None or storage_object.metadata is None:
            return

        etag = storage_object.metadata.etag

        if etag is not None:
            context.set(
                StorageKeys.ETAG,
                etag,
            )