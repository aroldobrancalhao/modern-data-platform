from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from collections.abc import Sequence


class CatalogProvider(ABC):
    """
    Defines the contract for metadata catalog providers.

    Implementations are responsible for exposing catalog
    operations independently of the underlying cloud.
    """

    @abstractmethod
    def database_exists(
        self,
        database: str,
    ) -> bool:
        """
        Returns True when the database exists.
        """
        raise NotImplementedError

    @abstractmethod
    def create_database(
        self,
        database: str,
        description: str | None = None,
    ) -> None:
        """
        Creates a database if it does not exist.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_database(
        self,
        database: str,
    ) -> None:
        """
        Deletes a database.
        """
        raise NotImplementedError

    @abstractmethod
    def list_databases(
        self,
    ) -> Sequence[str]:
        """
        Returns all available databases.
        """
        raise NotImplementedError

    @abstractmethod
    def table_exists(
        self,
        database: str,
        table: str,
    ) -> bool:
        """
        Returns True when a table exists.
        """
        raise NotImplementedError

    @abstractmethod
    def create_table(
        self,
        database: str,
        table: str,
        location: str,
        columns: list[dict],
        partition_keys: list[dict] | None = None,
    ) -> None:
        """
        Creates a metadata table.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_table(
        self,
        database: str,
        table: str,
    ) -> None:
        """
        Deletes a table.
        """
        raise NotImplementedError

    @abstractmethod
    def list_tables(
        self,
        database: str,
    ) -> Sequence[str]:
        """
        Lists all tables inside a database.
        """
        raise NotImplementedError

    @abstractmethod
    def get_table_location(
        self,
        database: str,
        table: str,
    ) -> str:
        """
        Returns the storage location of a table.
        """
        raise NotImplementedError

    @abstractmethod
    def update_table_location(
        self,
        database: str,
        table: str,
        location: str,
    ) -> None:
        """
        Updates table storage location.
        """
        raise NotImplementedError

    @abstractmethod
    def repair_table(
        self,
        database: str,
        table: str,
    ) -> None:
        """
        Refreshes table partitions.
        """
        raise NotImplementedError
