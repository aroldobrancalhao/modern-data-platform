from __future__ import annotations

from pathlib import Path
from typing import BinaryIO
from typing import Iterable

from data_platform.datalake.models.data_object import DataObject
from data_platform.datalake.models.datalake_location import DataLakeLocation
from data_platform.datalake.services.path_builder import PathBuilder
from data_platform.storage.models import StorageLocation
from data_platform.storage.models import StorageObject
from data_platform.storage.storage_provider import StorageProvider


class DataLakeService:
    """
    High-level service responsible for interacting with the Data Lake.

    This service delegates physical storage operations to a
    StorageProvider while PathBuilder is responsible for
    generating StorageLocation instances.
    """

    def __init__(
        self,
        *,
        storage_provider: StorageProvider,
        datalake: DataLakeLocation,
    ) -> None:
        self._storage = storage_provider
        self._datalake = datalake

    def location(
        self,
        *,
        object: DataObject,
    ) -> StorageLocation:
        """
        Returns the physical storage location of a logical object.
        """

        return PathBuilder.storage_location(
            datalake=self._datalake,
            data_object=object,
        )

    def exists(
        self,
        *,
        object: DataObject,
    ) -> bool:
        """
        Checks whether an object exists.
        """

        return self._storage.exists(
            self.location(
                object=object,
            )
        )

    def upload(
        self,
        *,
        object: DataObject,
        source: Path | BinaryIO,
    ) -> None:
        """
        Uploads an object.
        """

        self._storage.upload(
            location=self.location(
                object=object,
            ),
            source=source,
        )

    def download(
        self,
        *,
        object: DataObject,
        destination: Path,
    ) -> None:
        """
        Downloads an object.
        """

        self._storage.download(
            location=self.location(
                object=object,
            ),
            destination=destination,
        )

    def delete(
        self,
        *,
        object: DataObject,
    ) -> None:
        """
        Deletes an object.
        """

        self._storage.delete(
            self.location(
                object=object,
            )
        )

    def head(
        self,
        *,
        object: DataObject,
    ) -> StorageObject:
        """
        Returns object metadata.
        """

        return self._storage.head(
            self.location(
                object=object,
            )
        )

    def list(
        self,
        *,
        object: DataObject,
    ) -> Iterable[StorageObject]:
        """
        Lists objects under a dataset or partition.
        """

        return self._storage.list(
            self.location(
                object=object,
            )
        )

    def copy(
        self,
        *,
        source: StorageLocation,
        destination: StorageLocation,
    ) -> None:
        """
        Copies an object.
        """

        self._storage.copy(
            source=source,
            destination=destination,
        )

    def move(
        self,
        *,
        source: StorageLocation,
        destination: StorageLocation,
    ) -> None:
        """
        Moves an object.
        """

        self._storage.move(
            source=source,
            destination=destination,
        )