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

ingest_sources.ipynb's read_raw() is a plain `spark.read.parquet(path)`
over the whole raw/{entity}/ prefix, no dedup -- running this script
again while a raw/{entity}/ prefix already has an object from an
earlier run lands a second file next to it and double-counts every
row Postgres still has from that earlier extraction on any future
Bronze run (Postgres is cumulative here, nothing gets deleted, so
that's effectively all of them). Each raw/{entity}/ prefix must be
empty before running this -- delete any existing objects for the
entities you're about to extract first.

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
from data_platform.observability.logging_config import configure_logging
from data_platform.processing.logging.logging_hook import LoggingHook
from data_platform.processing.metrics.prometheus_metrics_hook import (
    PrometheusHook,
)
from data_platform.processing.tracing.tracing_hook import TracingHook
from data_platform.providers.provider_factory import ProviderFactory

from integrations.postgres.config import PostgresSettings

# entity -> "schema.table" (the table lives in the `marketplace`
# schema, not `public`).
ENTITIES: tuple[tuple[str, str], ...] = (
    ("customers", "marketplace.customers"),
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
    metrics_hook: PrometheusHook,
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

    executor = SequentialExecutor()
    executor.register_hooks(LoggingHook())
    executor.register_hooks(TracingHook())
    executor.register_hooks(metrics_hook)

    result = await executor.execute(pipeline, context)

    if result.status != ExecutionStatus.COMPLETED:
        stage_result = result.stage_results[0]
        raise SystemExit(
            f"Extraction failed for '{entity}': "
            f"{stage_result.error_type} - {stage_result.error_message}"
        )

    uri = context.get(StorageKeys.URI)
    print(f"OK: wrote {uri}")


async def main() -> None:
    configure_logging()

    provider_factory = ProviderFactory(
        registry=bootstrap(),
        settings=Settings(),
    )

    # One PrometheusHook shared across every entity in this run, so
    # all of them land in the same CollectorRegistry and are pushed
    # to the Pushgateway together, as a single batch, once the loop
    # is done.
    metrics_hook = PrometheusHook()

    for entity, table_name in ENTITIES:
        await _extract_one(entity, table_name, provider_factory, metrics_hook)

    metrics_hook.push(job="postgres_extraction_once")


if __name__ == "__main__":
    asyncio.run(main())
