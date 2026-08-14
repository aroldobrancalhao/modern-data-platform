"""
Modern Data Platform
Processing Framework

Silver catalog registration stage.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from data_platform.catalog import CatalogColumn, CatalogProvider, CatalogTable
from data_platform.catalog.exceptions import TableAlreadyExistsError
from data_platform.processing.context_writers.catalog_context_writer import (
    CatalogContextWriter,
)
from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult
from data_platform.storage.config import StorageConfig
from data_platform.storage.models import StorageLocation
from data_platform.storage.storage_provider import StorageProvider

_SPARK_TYPE_TO_GLUE_TYPE = {
    "string": "string",
    "long": "bigint",
    "integer": "int",
    "short": "smallint",
    "byte": "tinyint",
    "double": "double",
    "float": "float",
    "boolean": "boolean",
    "date": "date",
    "timestamp": "timestamp",
    "binary": "binary",
}


@dataclass(eq=False, slots=True, kw_only=True)
class SilverCatalogRegistrationStage(Stage):
    """
    Registers the Silver Delta table a Databricks Job just wrote
    (``silver/{entity}/``) into the Glue Catalog.

    Runs on the Airflow side, not inside the Databricks notebook --
    see docs/architecture/roadmap-next-steps.md for why (Databricks
    Free Edition has no AWS credential path from inside the cluster).

    Reads the table's schema straight from the Delta transaction log
    (``_delta_log/*.json``), through the already-resolved
    StorageProvider -- not via Spark (Airflow has no local Spark here)
    and not via a new Delta-reading dependency (deltalake/delta-rs is
    not installed). A Delta commit only re-emits a ``metaData`` action
    when the schema actually changes (confirmed empirically: a second
    ``overwrite`` with the same schema produces a commit with no
    ``metaData`` action at all), so the log is scanned from the
    newest commit backwards until one is found. This deliberately
    does not read Delta checkpoint files (``*.checkpoint.parquet``) --
    correct for a table that was just written by the Silver notebook,
    not a general-purpose Delta log reader.

    A missing Delta table (no Job silver run yet -- no ``_delta_log``
    objects at all) is a business failure -- retrying will not make
    it appear -- reported as a FAILED StageResult, mirroring
    BronzeIngestionStage. Any other error (S3/Glue permission,
    connectivity, an unmapped Spark type, or a table whose log has no
    ``metaData`` action in any retained commit) is left to propagate
    as a real exception.
    """

    storage_provider_name: str

    catalog_provider_name: str

    entity: str

    database: str = "mdp_silver_dev"

    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:

        storage_provider = cast(
            StorageProvider,
            self.resolve_provider(self.storage_provider_name),
        )

        location = StorageLocation.from_uri(
            StorageConfig.silver(self.entity)
        )

        schema = self._read_delta_schema(storage_provider, location)

        if schema is None:
            return StageResult(
                status=ExecutionStatus.FAILED,
                metadata=context.metadata,
                stage_id=self.id,
                stage_name=self.name,
                error_type="DeltaTableNotFoundError",
                error_message=(
                    f"No Delta table found at '{location.uri}' "
                    "(_delta_log is empty or missing)."
                ),
            )

        table = CatalogTable(
            database=self.database,
            name=self.entity,
            location=location,
            columns=[
                CatalogColumn(
                    name=field["name"],
                    type=self._to_glue_type(field["type"]),
                    nullable=field.get("nullable", True),
                )
                for field in schema["fields"]
            ],
            table_format="delta",
        )

        catalog_provider = cast(
            CatalogProvider,
            self.resolve_provider(self.catalog_provider_name),
        )

        try:
            catalog_provider.create_table(table)
        except TableAlreadyExistsError:
            # Idempotent re-registration: this stage's own docstring
            # already promises "re-running create_table for an
            # unchanged schema is harmless" (see
            # run_silver_catalog_registration_once.py's ENTITIES
            # comment) -- an already-registered table is a no-op here,
            # not a failure. Does not compare/update the existing
            # table's schema against this run's; a real schema change
            # needs update_table, not this stage.
            pass

        CatalogContextWriter.write_table(table, context)

        return StageResult(
            status=ExecutionStatus.COMPLETED,
            metadata=context.metadata,
            stage_id=self.id,
            stage_name=self.name,
        )

    @staticmethod
    def _read_delta_schema(
        provider: StorageProvider,
        table_location: StorageLocation,
    ) -> dict[str, Any] | None:
        """
        Returns the parsed ``schemaString`` from the most recent Delta
        commit that carries a ``metaData`` action, or None if the
        table has no ``_delta_log`` at all.
        """

        log_location = StorageLocation(
            scheme=table_location.scheme,
            bucket=table_location.bucket,
            key=f"{table_location.key}/_delta_log/",
        )

        commits = sorted(
            (
                storage_object.location
                for storage_object in provider.list(log_location)
                if storage_object.location.name.endswith(".json")
            ),
            key=lambda commit_location: commit_location.name,
            reverse=True,
        )

        if not commits:
            return None

        with tempfile.TemporaryDirectory() as tmp_dir:

            for commit_location in commits:

                destination = Path(tmp_dir) / commit_location.name

                provider.download(commit_location, destination)

                for line in destination.read_text().splitlines():

                    if not line.strip():
                        continue

                    action = json.loads(line)

                    if "metaData" in action:
                        return cast(
                            "dict[str, Any]",
                            json.loads(
                                action["metaData"]["schemaString"]
                            ),
                        )

        raise RuntimeError(
            "No metaData action found in any Delta commit under "
            f"'{log_location.uri}'."
        )

    @staticmethod
    def _to_glue_type(spark_type: object) -> str:

        if isinstance(spark_type, str):

            if spark_type in _SPARK_TYPE_TO_GLUE_TYPE:
                return _SPARK_TYPE_TO_GLUE_TYPE[spark_type]

            if spark_type.startswith("decimal("):
                return spark_type

        raise ValueError(
            "Unsupported Delta/Spark type for Glue registration: "
            f"{spark_type!r}."
        )
