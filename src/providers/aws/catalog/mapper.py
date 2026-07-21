from __future__ import annotations

from typing import Any

from platform.catalog import CatalogColumn
from platform.catalog import CatalogDatabase
from platform.catalog import CatalogTable
from platform.storage.models import StorageLocation


class GlueCatalogMapper:

    @staticmethod
    def to_catalog_database(
        database: dict[str, Any],
    ) -> CatalogDatabase:

        location = database.get("LocationUri")

        return CatalogDatabase(
            name=database["Name"],
            description=database.get("Description"),
            location=(
                StorageLocation.from_uri(location)
                if location
                else None
            ),
        )

    @staticmethod
    def to_catalog_table(
        table: dict[str, Any],
    ) -> CatalogTable:

        storage = table["StorageDescriptor"]

        return CatalogTable(
            database=table["DatabaseName"],
            name=table["Name"],
            description=table.get("Description"),
            location=StorageLocation.from_uri(
                storage["Location"],
            ),
            columns=[
                GlueCatalogMapper.to_catalog_column(column)
                for column in storage.get("Columns", [])
            ],
            partitions=[
                partition["Name"]
                for partition in table.get(
                    "PartitionKeys",
                    [],
                )
            ],
        )

    @staticmethod
    def to_catalog_column(
        column: dict[str, Any],
    ) -> CatalogColumn:

        return CatalogColumn(
            name=column["Name"],
            type=column["Type"],
            nullable=True,
            comment=column.get("Comment"),
        )

    @staticmethod
    def to_glue_database(
        database: CatalogDatabase,
    ) -> dict[str, Any]:

        result: dict[str, Any] = {
            "Name": database.name,
        }

        if database.description:
            result["Description"] = database.description

        if database.location:
            result["LocationUri"] = str(database.location)

        return result

    @staticmethod
    def to_glue_table(
        table: CatalogTable,
    ) -> dict[str, Any]:

        return {
            "Name": table.name,
            "Description": table.description,
            "StorageDescriptor": {
                "Columns": [
                    GlueCatalogMapper.to_glue_column(column)
                    for column in table.columns
                ],
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
            "PartitionKeys": [
                {
                    "Name": partition,
                    "Type": "string",
                }
                for partition in table.partitions
            ],
            "TableType": "EXTERNAL_TABLE",
        }

    @staticmethod
    def to_glue_column(
        column: CatalogColumn,
    ) -> dict[str, Any]:

        result = {
            "Name": column.name,
            "Type": column.type,
        }

        if column.comment:
            result["Comment"] = column.comment

        return result