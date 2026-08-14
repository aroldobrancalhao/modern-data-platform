"""
Modern Data Platform

One-off script: runs SilverCatalogRegistrationStage once per entity
against the real Silver Delta tables (silver/{entity}/) and the real
Glue Catalog (mdp_silver_dev), on the Airflow side -- the real local
AWS credential chain already works here, unlike inside the Databricks
cluster (see docs/architecture/roadmap-next-steps.md).

ENTITIES excludes "customers": it was already registered in an
earlier run (see ADR-011 migration) -- re-running create_table for an
unchanged schema is harmless, but there's no need to repeat it here.

Run with:

    uv run python scripts/run_silver_catalog_registration_once.py

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import asyncio

from data_platform.bootstrap import bootstrap
from data_platform.config.settings import Settings
from data_platform.processing.catalog.silver_catalog_registration_stage import (
    SilverCatalogRegistrationStage,
)
from data_platform.processing.core.context_keys.catalog_keys import (
    CatalogKeys,
)
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
from data_platform.observability.logging_config import configure_logging
from data_platform.processing.logging.logging_hook import LoggingHook
from data_platform.processing.metrics.prometheus_metrics_hook import (
    PrometheusHook,
)
from data_platform.processing.tracing.tracing_hook import TracingHook
from data_platform.providers.provider_factory import ProviderFactory

DATABASE = "mdp_silver_dev"

ENTITIES: tuple[str, ...] = (
    "orders",
    "order_items",
    "products",
    "payments",
    "sellers",
    "categories",
    "order_status_history",
)


async def _register_one(
    entity: str,
    provider_factory: ProviderFactory,
    metrics_hook: PrometheusHook,
) -> None:
    stage = SilverCatalogRegistrationStage(
        id=f"register-silver-{entity}-once",
        name=f"Register Silver {entity.title()} (one-off)",
        storage_provider_name="aws.s3",
        catalog_provider_name="aws.glue",
        entity=entity,
        database=DATABASE,
        provider_factory=provider_factory,
    )

    pipeline = Pipeline(
        id=f"silver-catalog-registration-once-{entity}",
        name=f"Silver Catalog Registration (one-off) - {entity}",
        stages=(stage,),
    )

    context = ProcessingContext(
        id=f"context-silver-catalog-registration-once-{entity}",
        metadata=ExecutionMetadata(
            execution_id=f"execution-silver-catalog-registration-once-{entity}",
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
            f"Registration failed for '{entity}': "
            f"{stage_result.error_type} - {stage_result.error_message}"
        )

    print(
        f"OK: registered {context.get(CatalogKeys.DATABASE)}."
        f"{context.get(CatalogKeys.TABLE)}"
    )


async def main() -> None:
    configure_logging()

    provider_factory = ProviderFactory(
        registry=bootstrap(),
        settings=Settings(),
    )

    # One PrometheusHook shared across every entity in this run --
    # see run_postgres_extraction_once.py's main() for why.
    metrics_hook = PrometheusHook()

    for entity in ENTITIES:
        await _register_one(entity, provider_factory, metrics_hook)

    metrics_hook.push(job="silver_catalog_registration_once")


if __name__ == "__main__":
    asyncio.run(main())
