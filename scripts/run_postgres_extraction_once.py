"""
Modern Data Platform

One-off script: runs PostgresExtractionStage once per entity against
the real local Postgres (marketplace.*) and the real S3 bucket,
landing a persistent file in raw/{entity}/ for each -- unlike the
pytest integration test for this Stage, this does NOT clean up
afterwards.

This exists to seed raw/ with real objects before a real Databricks
full_pipeline run: ingest_sources.ipynb needs something under
raw/{entity}/ to read.

ENTITIES intentionally excludes "customers": it already went through
raw -> bronze -> silver -> Glue in an earlier run (raw/customers/ has
one object already), and ingest_sources.ipynb's read_raw() is a plain
`spark.read.parquet(path)` over the whole raw/{entity}/ prefix -- a
second extraction would land a second file next to it and double-count
rows on any future Bronze run for customers. Re-run this for customers
only if that raw object is ever removed first.

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

# entity -> "schema.table" (the table lives in the `marketplace`
# schema, not `public`).
ENTITIES: tuple[tuple[str, str], ...] = (
    ("orders", "marketplace.orders"),
    ("order_items", "marketplace.order_items"),
    ("products", "marketplace.products"),
    ("payments", "marketplace.payments"),
    ("sellers", "marketplace.sellers"),
    ("categories", "marketplace.categories"),
)


async def _extract_one(
    entity: str,
    table_name: str,
    provider_factory: ProviderFactory,
) -> None:
    stage = PostgresExtractionStage(
        id=f"extract-{entity}-once",
        name=f"Extract {entity.title()} (one-off)",
        provider_name="aws.s3",
        postgres_settings=PostgresSettings(),
        table_name=table_name,
        entity=entity,
        provider_factory=provider_factory,
    )

    pipeline = Pipeline(
        id=f"postgres-extraction-once-{entity}",
        name=f"Postgres Extraction (one-off) - {entity}",
        stages=(stage,),
    )

    context = ProcessingContext(
        id=f"context-postgres-extraction-once-{entity}",
        metadata=ExecutionMetadata(
            execution_id=f"execution-postgres-extraction-once-{entity}",
        ),
    )

    result = await SequentialExecutor().execute(pipeline, context)

    if result.status != ExecutionStatus.COMPLETED:
        stage_result = result.stage_results[0]
        raise SystemExit(
            f"Extraction failed for '{entity}': "
            f"{stage_result.error_type} - {stage_result.error_message}"
        )

    uri = context.get(StorageKeys.URI)
    print(f"OK: wrote {uri}")


async def main() -> None:
    provider_factory = ProviderFactory(
        registry=bootstrap(),
        settings=Settings(),
    )

    for entity, table_name in ENTITIES:
        await _extract_one(entity, table_name, provider_factory)


if __name__ == "__main__":
    asyncio.run(main())
