"""
Modern Data Platform

One-off script: runs PostgresExtractionStage once against the real
local Postgres (marketplace.customers) and the real S3 bucket,
landing a persistent file in raw/customers/ -- unlike the pytest
integration test for this Stage, this does NOT clean up afterwards.

This exists to seed raw/ with a real object before the first real
Databricks full_pipeline run: as of this run, nothing exists yet under
s3://mdp-datalake-dev-857854758128/raw/, and ingest_sources.ipynb
needs something there to read.

Run with:

    uv run python scripts/run_postgres_extraction_once.py

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import asyncio

from data_platform.bootstrap import bootstrap
from data_platform.config.settings import Settings
from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.executor.sequential_executor import (
    SequentialExecutor,
)
from data_platform.processing.extraction.postgres_extraction_stage import (
    PostgresExtractionStage,
)
from data_platform.processing.core.context_keys.storage_keys import (
    StorageKeys,
)
from data_platform.providers.provider_factory import ProviderFactory

from integrations.postgres.config import PostgresSettings

ENTITY = "customers"

# The table lives in the `marketplace` schema, not `public` -- matches
# tests/integration/aws/test_postgres_extraction_stage_real.py.
TABLE_NAME = "marketplace.customers"


async def main() -> None:
    provider_factory = ProviderFactory(
        registry=bootstrap(),
        settings=Settings(),
    )

    stage = PostgresExtractionStage(
        id="extract-customers-once",
        name="Extract Customers (one-off)",
        provider_name="aws.s3",
        postgres_settings=PostgresSettings(),
        table_name=TABLE_NAME,
        entity=ENTITY,
        provider_factory=provider_factory,
    )

    pipeline = Pipeline(
        id="postgres-extraction-once",
        name="Postgres Extraction (one-off)",
        stages=(stage,),
    )

    context = ProcessingContext(
        id="context-postgres-extraction-once",
        metadata=ExecutionMetadata(
            execution_id="execution-postgres-extraction-once",
        ),
    )

    result = await SequentialExecutor().execute(pipeline, context)

    if result.status != ExecutionStatus.COMPLETED:
        stage_result = result.stage_results[0]
        raise SystemExit(
            f"Extraction failed: {stage_result.error_type} - "
            f"{stage_result.error_message}"
        )

    uri = context.get(StorageKeys.URI)
    print(f"OK: wrote {uri}")


if __name__ == "__main__":
    asyncio.run(main())
