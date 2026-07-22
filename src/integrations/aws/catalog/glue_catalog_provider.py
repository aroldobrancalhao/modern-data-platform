from __future__ import annotations

from typing import Any

from data_platform.catalog import CatalogColumn
from data_platform.catalog import CatalogDatabase
from data_platform.catalog import CatalogProvider
from data_platform.catalog import CatalogTable
from data_platform.catalog.exceptions import (
    DatabaseAlreadyExistsError,
    DatabaseNotFoundError,
    TableAlreadyExistsError,
    TableNotFoundError,
)
from data_platform.contracts.base_provider import BaseProvider
from data_platform.storage.models import StorageLocation
from data_platform.types import PlatformProvider

from integrations.aws.core.aws_context import AwsContext


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
        database: CatalogDatabase,
    ) -> None:

        if self.database_exists(database.name):
            raise DatabaseAlreadyExistsError(database.name)

        database_input: dict[str, Any] = {
            "Name": database.name,
        }

        if database.description:
            database_input["Description"] = database.description

        if database.location:
            database_input["LocationUri"] = str(database.location)

        self._client.create_database(
            DatabaseInput=database_input,
        )

    def get_database(
        self,
        database: str,
    ) -> CatalogDatabase:

        if not self.database_exists(database):
            raise DatabaseNotFoundError(database)

        response = self._client.get_database(Name=database)

        data = response["Database"]

        location = data.get("LocationUri")

        return CatalogDatabase(
            name=data["Name"],
            description=data.get("Description"),
            location=StorageLocation.from_uri(location)
            if location
            else None,
        )

    def delete_database(
        self,
        database: str,
    ) -> None:

        if not self.database_exists(database):
            raise DatabaseNotFoundError(database)

        self._client.delete_database(Name=database)

    def list_databases(self) -> list[CatalogDatabase]:

        paginator = self._client.get_paginator("get_databases")

        databases: list[CatalogDatabase] = []

        for page in paginator.paginate():

            for database in page["DatabaseList"]:

                location = database.get("LocationUri")

                databases.append(
                    CatalogDatabase(
                        name=database["Name"],
                        description=database.get("Description"),
                        location=StorageLocation.from_uri(location)
                        if location
                        else None,
                    )
                )

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
        table: CatalogTable,
    ) -> None:

        if self.table_exists(table.database, table.name):
            raise TableAlreadyExistsError(table.name)

        columns = [
            {
                "Name": column.name,
                "Type": column.type,
                **(
                    {"Comment": column.comment}
                    if column.comment
                    else {}
                ),
            }
            for column in table.columns
        ]

        partition_keys = [
            {
                "Name": partition,
                "Type": "string",
            }
            for partition in table.partitions
        ]

        self._client.create_table(
            DatabaseName=table.database,
            TableInput={
                "Name": table.name,
                "Description": table.description,
                "StorageDescriptor": {
                    "Columns": columns,
                    "Location": str(table.location),
                    "InputFormat": (
                        "org.apache.hadoop.mapred.TextInputFormat"
                    ),
                    "OutputFormat": (
                        "org.apache.hadoop.hive.ql.io."
                        "HiveIgnoreKeyTextOutputFormat"
                    ),
                    "SerdeInfo": {
                        "SerializationLibrary": (
                            "org.apache.hadoop.hive.serde2.lazy."
                            "LazySimpleSerDe"
                        ),
                    },
                },
                "PartitionKeys": partition_keys,
                "TableType": "EXTERNAL_TABLE",
            },
        )

    def get_table(
        self,
        database: str,
        table: str,
    ) -> CatalogTable:

        if not self.table_exists(database, table):
            raise TableNotFoundError(table)

        response = self._client.get_table(
            DatabaseName=database,
            Name=table,
        )

        data = response["Table"]
        storage = data["StorageDescriptor"]

        return CatalogTable(
            database=database,
            name=data["Name"],
            description=data.get("Description"),
            location=StorageLocation.from_uri(
                storage["Location"],
            ),
            columns=[
                CatalogColumn(
                    name=column["Name"],
                    type=column["Type"],
                    nullable=True,
                    comment=column.get("Comment"),
                )
                for column in storage.get("Columns", [])
            ],
            partitions=[
                partition["Name"]
                for partition in data.get(
                    "PartitionKeys",
                    [],
                )
            ],
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
    ) -> list[CatalogTable]:

        paginator = self._client.get_paginator(
            "get_tables",
        )

        tables: list[CatalogTable] = []

        for page in paginator.paginate(
            DatabaseName=database,
        ):
            for data in page["TableList"]:

                storage = data["StorageDescriptor"]

                tables.append(
                    CatalogTable(
                        database=database,
                        name=data["Name"],
                        description=data.get(
                            "Description",
                        ),
                        location=StorageLocation.from_uri(
                            storage["Location"],
                        ),
                        columns=[
                            CatalogColumn(
                                name=column["Name"],
                                type=column["Type"],
                                nullable=True,
                                comment=column.get(
                                    "Comment",
                                ),
                            )
                            for column in storage.get(
                                "Columns",
                                [],
                            )
                        ],
                        partitions=[
                            partition["Name"]
                            for partition in data.get(
                                "PartitionKeys",
                                [],
                            )
                        ],
                    )
                )

        return tables

    def get_table_location(
        self,
        database: str,
        table: str,
    ) -> StorageLocation:

        return self.get_table(
            database,
            table,
        ).location

    def update_table_location(
        self,
        database: str,
        table: str,
        location: StorageLocation,
    ) -> None:

        response = self._client.get_table(
            DatabaseName=database,
            Name=table,
        )

        table_input = response["Table"]

        table_input["StorageDescriptor"][
            "Location"
        ] = str(location)

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
        raise NotImplementedError(
            "Glue Catalog does not support repair_table."
        )