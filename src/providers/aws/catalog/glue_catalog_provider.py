from __future__ import annotations

from collections.abc import Sequence

from typing import Any

from platform.catalog.catalog_provider import CatalogProvider
from platform.catalog.exceptions import (
    DatabaseAlreadyExistsError,
    DatabaseNotFoundError,
    TableAlreadyExistsError,
    TableNotFoundError,
)
from platform.contracts.base_provider import BaseProvider
from platform.types import PlatformProvider

from providers.aws.core.aws_context import AwsContext


class GlueCatalogProvider(BaseProvider, CatalogProvider):
    """
    AWS Glue implementation of the CatalogProvider.
    """

    provider = PlatformProvider.AWS

    def __init__(self, context: AwsContext) -> None:
        self._context = context
        self._client = context.client("glue")

    #
    # Databases
    #

    def database_exists(self, database: str) -> bool:
        try:
            self._client.get_database(Name=database)
            return True

        except self._client.exceptions.EntityNotFoundException:
            return False

    def create_database(
        self,
        database: str,
        description: str | None = None,
    ) -> None:

        if self.database_exists(database):
            raise DatabaseAlreadyExistsError(database)

        database_input: dict[str, Any] = {
            "Name": database,
        }

        if description:
            database_input["Description"] = description

        self._client.create_database(
            DatabaseInput=database_input,
        )

    def delete_database(self, database: str) -> None:

        if not self.database_exists(database):
            raise DatabaseNotFoundError(database)

        self._client.delete_database(Name=database)

    def list_databases(self) -> Sequence[str]:

        paginator = self._client.get_paginator("get_databases")

        databases: list[str] = []

        for page in paginator.paginate():
            databases.extend(database["Name"] for database in page["DatabaseList"])

        return databases

    #
    # Tables
    #

    def table_exists(
        self,
        database: str,
        table: str,
    ) -> bool:

        try:
            self._client.get_table(
                DatabaseName=database,
                Name=table,
            )

            return True

        except self._client.exceptions.EntityNotFoundException:
            return False

    def create_table(
        self,
        database: str,
        table: str,
        location: str,
        columns: list[dict],
        partition_keys: list[dict] | None = None,
    ) -> None:

        if self.table_exists(database, table):
            raise TableAlreadyExistsError(table)

        self._client.create_table(
            DatabaseName=database,
            TableInput={
                "Name": table,
                "StorageDescriptor": {
                    "Columns": columns,
                    "Location": location,
                    "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
                    "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                    "SerdeInfo": {
                        "SerializationLibrary": "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe",
                    },
                },
                "PartitionKeys": partition_keys or [],
                "TableType": "EXTERNAL_TABLE",
            },
        )

    def delete_table(
        self,
        database: str,
        table: str,
    ) -> None:

        if not self.table_exists(database, table):
            raise TableNotFoundError(table)

        self._client.delete_table(
            DatabaseName=database,
            Name=table,
        )

    def list_tables(
        self,
        database: str,
    ) -> Sequence[str]:

        paginator = self._client.get_paginator("get_tables")

        tables: list[str] = []

        for page in paginator.paginate(DatabaseName=database):
            tables.extend(table["Name"] for table in page["TableList"])

        return tables

    def get_table_location(
        self,
        database: str,
        table: str,
    ) -> str:

        if not self.table_exists(database, table):
            raise TableNotFoundError(table)

        response = self._client.get_table(
            DatabaseName=database,
            Name=table,
        )

        return response["Table"]["StorageDescriptor"]["Location"]

    def update_table_location(
        self,
        database: str,
        table: str,
        location: str,
    ) -> None:

        response = self._client.get_table(
            DatabaseName=database,
            Name=table,
        )

        table_input = response["Table"]

        table_input["StorageDescriptor"]["Location"] = location

        for field in (
            "DatabaseName",
            "CreateTime",
            "UpdateTime",
            "CreatedBy",
            "VersionId",
            "CatalogId",
            "IsRegisteredWithLakeFormation",
        ):
            table_input.pop(field, None)

        self._client.update_table(
            DatabaseName=database,
            TableInput=table_input,
        )

    def repair_table(
        self,
        database: str,
        table: str,
    ) -> None:
        """
        AWS Glue has no native MSCK REPAIR equivalent.

        This method intentionally exists to keep the
        provider contract cloud-agnostic.
        """

        return
