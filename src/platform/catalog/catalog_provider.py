from abc import ABC
from abc import abstractmethod

from platform.catalog.models import CatalogDatabase
from platform.catalog.models import CatalogTable
from platform.storage.models import StorageLocation


class CatalogProvider(ABC):
    """
    Abstract catalog provider.

    Defines the contract for metadata catalogs such as AWS Glue,
    Databricks Unity Catalog and Hive Metastore.
    """

    #
    # Databases
    #

    @abstractmethod
    def database_exists(
        self,
        database: str,
    ) -> bool:
        """
        Returns True if the database exists.
        """
        ...

    @abstractmethod
    def create_database(
        self,
        database: CatalogDatabase,
    ) -> None:
        """
        Creates a database.
        """
        ...

    @abstractmethod
    def delete_database(
        self,
        database: str,
    ) -> None:
        """
        Deletes a database.
        """
        ...

    @abstractmethod
    def get_database(
        self,
        database: str,
    ) -> CatalogDatabase:
        """
        Returns a database definition.
        """
        ...

    @abstractmethod
    def list_databases(self) -> list[CatalogDatabase]:
        """
        Lists all databases.
        """
        ...

    #
    # Tables
    #

    @abstractmethod
    def table_exists(
        self,
        database: str,
        table: str,
    ) -> bool:
        """
        Returns True if the table exists.
        """
        ...

    @abstractmethod
    def create_table(
        self,
        table: CatalogTable,
    ) -> None:
        """
        Creates a table.
        """
        ...

    @abstractmethod
    def delete_table(
        self,
        database: str,
        table: str,
    ) -> None:
        """
        Deletes a table.
        """
        ...

    @abstractmethod
    def get_table(
        self,
        database: str,
        table: str,
    ) -> CatalogTable:
        """
        Returns a table definition.
        """
        ...

    @abstractmethod
    def list_tables(
        self,
        database: str,
    ) -> list[CatalogTable]:
        """
        Lists all tables inside a database.
        """
        ...

    @abstractmethod
    def get_table_location(
        self,
        database: str,
        table: str,
    ) -> StorageLocation:
        """
        Returns the physical storage location of a table.
        """
        ...

    @abstractmethod
    def update_table_location(
        self,
        database: str,
        table: str,
        location: StorageLocation,
    ) -> None:
        """
        Updates the physical storage location of a table.
        """
        ...

    @abstractmethod
    def repair_table(
        self,
        database: str,
        table: str,
    ) -> None:
        """
        Repairs table metadata.
        """
        ...