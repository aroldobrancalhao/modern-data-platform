"""
Modern Data Platform

One-off script: runs GoldCatalogRegistrationStage once against the
real Gold Delta table (gold/customers/) and the real Glue Catalog
(mdp_gold_dev), on the Airflow side -- the real local AWS credential
chain already works here, unlike inside the Databricks cluster (see
docs/architecture/roadmap-next-steps.md).

Run with:

    uv run python scripts/run_gold_catalog_registration_once.py

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import asyncio

from data_platform.bootstrap import bootstrap
from data_platform.config.settings import Settings
from data_platform.processing.catalog.gold_catalog_registration_stage import (
    GoldCatalogRegistrationStage,
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
from data_platform.providers.provider_factory import ProviderFactory

ENTITY = "customers"
DATABASE = "mdp_gold_dev"


async def main() -> None:
    provider_factory = ProviderFactory(
        registry=bootstrap(),
        settings=Settings(),
    )

    stage = GoldCatalogRegistrationStage(
        id="register-gold-customers-once",
        name="Register Gold Customers (one-off)",
        storage_provider_name="aws.s3",
        catalog_provider_name="aws.glue",
        entity=ENTITY,
        database=DATABASE,
        provider_factory=provider_factory,
    )

    pipeline = Pipeline(
        id="gold-catalog-registration-once",
        name="Gold Catalog Registration (one-off)",
        stages=(stage,),
    )

    context = ProcessingContext(
        id="context-gold-catalog-registration-once",
        metadata=ExecutionMetadata(
            execution_id="execution-gold-catalog-registration-once",
        ),
    )

    result = await SequentialExecutor().execute(pipeline, context)

    if result.status != ExecutionStatus.COMPLETED:
        stage_result = result.stage_results[0]
        raise SystemExit(
            f"Registration failed: {stage_result.error_type} - "
            f"{stage_result.error_message}"
        )

    print(
        f"OK: registered {context.get(CatalogKeys.DATABASE)}."
        f"{context.get(CatalogKeys.TABLE)}"
    )


if __name__ == "__main__":
    asyncio.run(main())
