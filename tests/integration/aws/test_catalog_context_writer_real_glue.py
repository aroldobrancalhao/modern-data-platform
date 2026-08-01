"""
Modern Data Platform
Processing Framework

Real-AWS smoke test for the Catalog (Glue) chain.

Proves the ADR-010 execution chain closes end to end against the
actual provisioned Glue database (mdp_bronze_dev, sa-east-1) and a
real GlueCatalogProvider -- not a fake.

Reuses the `real_aws` marker (S3 and Glue share the same AWS
account/credentials), excluded from the default suite. Run it
explicitly with:

    uv run pytest tests/integration/aws/test_catalog_context_writer_real_glue.py -m real_aws -v

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import cast

import pytest

from data_platform.bootstrap import bootstrap
from data_platform.catalog import CatalogColumn, CatalogProvider, CatalogTable
from data_platform.config.settings import Settings
from data_platform.processing.context_writers.catalog_context_writer import (
    CatalogContextWriter,
)
from data_platform.processing.core.context_keys.catalog_keys import (
    CatalogKeys,
)
from data_platform.processing.core.context_keys.processing_keys import (
    ProcessingKeys,
)
from data_platform.processing.core.execution_metadata import (
    ExecutionMetadata,
)
from data_platform.processing.core.execution_status import ExecutionStatus
from data_platform.processing.core.pipeline import Pipeline
from data_platform.processing.core.pipeline_result import PipelineResult
from data_platform.processing.core.processing_context import (
    ProcessingContext,
)
from data_platform.processing.core.stage import Stage
from data_platform.processing.core.stage_result import StageResult
from data_platform.processing.executor.sequential_executor import (
    SequentialExecutor,
)
from data_platform.providers.provider_factory import ProviderFactory
from data_platform.storage.config import StorageSettings
from data_platform.storage.models import StorageLocation

pytestmark = [pytest.mark.anyio, pytest.mark.real_aws]

DATABASE = "mdp_bronze_dev"
BUCKET = StorageSettings().default_bucket


@dataclass(eq=False, slots=True, kw_only=True)
class CatalogPublishingStage(Stage):
    """
    Minimal concrete Stage used only to prove that a CatalogTable read
    from a real CatalogProvider (resolved through the Stage's
    ProviderFactory) is correctly published into the ProcessingContext
    by CatalogContextWriter.
    """

    provider_name: str

    database: str

    table_name: str

    async def execute(
        self,
        context: ProcessingContext,
    ) -> StageResult:

        provider = self.resolve_provider(self.provider_name)
        assert isinstance(provider, CatalogProvider)

        table = provider.get_table(self.database, self.table_name)

        CatalogContextWriter.write_table(table, context)

        return StageResult(
            status=ExecutionStatus.COMPLETED,
            metadata=context.metadata,
            stage_id=self.id,
            stage_name=self.name,
        )


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture
def provider_factory() -> ProviderFactory:
    return ProviderFactory(
        registry=bootstrap(),
        settings=Settings(),
    )


@pytest.fixture
def catalog_provider(
    provider_factory: ProviderFactory,
) -> CatalogProvider:
    return cast(
        CatalogProvider,
        provider_factory.create("aws.glue"),
    )


@pytest.fixture
def table(
    catalog_provider: CatalogProvider,
) -> Iterator[CatalogTable]:
    table_name = f"_smoke_test_{uuid.uuid4().hex}"

    smoke_test_table = CatalogTable(
        database=DATABASE,
        name=table_name,
        location=StorageLocation(
            scheme="s3",
            bucket=BUCKET,
            key=f"bronze/_smoke_test/{table_name}/",
        ),
        columns=[
            CatalogColumn(name="id", type="string"),
        ],
        table_format="generic",
    )

    try:
        yield smoke_test_table
    finally:
        if catalog_provider.table_exists(
            smoke_test_table.database,
            smoke_test_table.name,
        ):
            catalog_provider.delete_table(
                smoke_test_table.database,
                smoke_test_table.name,
            )


def create_context() -> ProcessingContext:
    return ProcessingContext(
        id="context-real-glue-smoke-test",
        metadata=ExecutionMetadata(
            execution_id="execution-real-glue-smoke-test",
        ),
    )


# ----------------------------------------------------------------------
# Scenario
# ----------------------------------------------------------------------


async def test_catalog_table_is_published_into_the_processing_context(
    catalog_provider: CatalogProvider,
    provider_factory: ProviderFactory,
    table: CatalogTable,
) -> None:
    catalog_provider.create_table(table)

    stage = CatalogPublishingStage(
        id="publish-smoke-test-table",
        name="Publish Smoke Test Table",
        provider_name="aws.glue",
        database=table.database,
        table_name=table.name,
        provider_factory=provider_factory,
    )

    pipeline = Pipeline(
        id="catalog-smoke-test",
        name="Catalog Smoke Test",
        stages=(stage,),
    )

    context = create_context()

    result = await SequentialExecutor().execute(pipeline, context)

    assert result.status == ExecutionStatus.COMPLETED
    assert context.get(CatalogKeys.DATABASE) == DATABASE
    assert context.get(CatalogKeys.TABLE) == table.name

    pipeline_result = context.get(ProcessingKeys.PIPELINE_RESULT)
    assert isinstance(pipeline_result, PipelineResult)
    assert pipeline_result is result
    assert pipeline_result.status == ExecutionStatus.COMPLETED

    # Independent confirmation, after the pipeline ran, that the table
    # genuinely exists in Glue (not just that the Stage's own
    # get_table() call happened to succeed).
    persisted = catalog_provider.get_table(table.database, table.name)
    assert persisted.name == table.name
