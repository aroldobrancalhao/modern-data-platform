from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import BinaryIO
from typing import Iterable

from platform.storage.models import StorageLocation
from platform.storage.models import StorageObject


class StorageProvider(ABC):
    """
    Defines the contract for storage providers.
    """

    @abstractmethod
    def exists(
        self,
        location: StorageLocation,
    ) -> bool:
        """
        Checks whether an object exists.
        """

    @abstractmethod
    def upload(
        self,
        location: StorageLocation,
        source: Path | BinaryIO,
    ) -> None:
        """
        Uploads an object.
        """

    @abstractmethod
    def download(
        self,
        location: StorageLocation,
        destination: Path,
    ) -> None:
        """
        Downloads an object.
        """

    @abstractmethod
    def delete(
        self,
        location: StorageLocation,
    ) -> None:
        """
        Deletes an object.
        """

    @abstractmethod
    def copy(
        self,
        source: StorageLocation,
        destination: StorageLocation,
    ) -> None:
        """
        Copies an object.
        """

    @abstractmethod
    def move(
        self,
        source: StorageLocation,
        destination: StorageLocation,
    ) -> None:
        """
        Moves an object.
        """

    @abstractmethod
    def list(
        self,
        location: StorageLocation,
    ) -> Iterable[StorageObject]:
        """
        Lists objects.
        """

    @abstractmethod
    def head(
        self,
        location: StorageLocation,
    ) -> StorageObject:
        """
        Returns object metadata.
        """
