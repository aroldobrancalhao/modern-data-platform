"""
Modern Data Platform
Processing Framework

Publishes CatalogProvider results into the ProcessingContext.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.catalog.models import CatalogDatabase, CatalogTable
from data_platform.processing.core.context_keys.catalog_keys import (
    CatalogKeys,
)
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)


class CatalogContextWriter:
    """
    Translates a CatalogDatabase/CatalogTable into CatalogKeys and
    publishes them into the ProcessingContext.

    This class knows about CatalogDatabase/CatalogTable (provider-
    agnostic domain models) and about ProcessingContext/CatalogKeys. It
    does not know about any concrete CatalogProvider (Glue, Hive
    Metastore, Unity Catalog, ...) -- the caller is responsible for
    obtaining the database/table from a Provider and passing it here.

    Only CatalogKeys.DATABASE and CatalogKeys.TABLE are populated
    today. CatalogKeys.CATALOG, SCHEMA and VIEW are intentionally left
    unset: the current catalog model (AWS Glue, via GlueCatalogProvider)
    does not expose a "catalog" or "schema" concept distinct from
    "database", nor a "view" concept distinct from "table".
    """

    @staticmethod
    def write_database(
        database: CatalogDatabase,
        context: ProcessingContext,
    ) -> None:
        """
        Publishes a CatalogDatabase into the ProcessingContext.
        """

        context.set(
            CatalogKeys.DATABASE,
            database.name,
        )

    @staticmethod
    def write_table(
        table: CatalogTable,
        context: ProcessingContext,
    ) -> None:
        """
        Publishes a CatalogTable into the ProcessingContext.

        Also publishes the table's database (CatalogKeys.DATABASE),
        since CatalogTable always carries it.
        """

        context.set(
            CatalogKeys.DATABASE,
            table.database,
        )

        context.set(
            CatalogKeys.TABLE,
            table.name,
        )