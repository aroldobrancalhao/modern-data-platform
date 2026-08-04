"""
Modern Data Platform

Real batch pipeline DAG -- orchestrates, in order, the same steps
already run manually throughout Sprint 5's validation:

    Postgres extraction (7 entities)
        -> Databricks "Full Pipeline" job (bronze -> bronze_validate
           -> bronze_optimize -> silver)
        -> dbt run --select gold
        -> dbt test --select gold

Per ADR-0008, Airflow is responsible only for orchestration -- the
extraction step reuses PostgresExtractionStage/Pipeline directly (the
same Stage scripts/run_postgres_extraction_once.py calls, imported
from /opt/mdp/src, mounted read-only into every Airflow container),
the Databricks step calls the real "Full Pipeline" job via the
databricks_default Connection (a dedicated PAT, see
airflow/config/bootstrap/airflow.py), and the dbt steps shell out to
the real dbt CLI against the real Athena warehouse (credentials via
the AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY env vars every Airflow
container now has -- boto3's own default credential chain, same key
already used by every manual `aws`/`dbt` command in this project).

Each task's success is verified for real, not just "did not raise":

- extract_postgres re-queries Postgres' own row count per entity and
  compares it against the landed parquet's row count (read back from
  S3), raising on any mismatch. It also clears any pre-existing
  raw/{entity}/ objects first, since PostgresExtractionStage always
  appends a new file and the Databricks notebook that reads raw/ has
  no dedup -- this is what makes the DAG safely re-runnable, an
  orchestration-level idempotency concern, not a change to the
  Stage's own contract.
- run_databricks_full_pipeline uses DatabricksRunNowOperator's default
  wait_for_termination=True, which polls the real job run and fails
  the task unless Databricks itself reports a SUCCESS terminal state
  across every task in the job (bronze, bronze_validate,
  bronze_optimize, silver) -- bronze_validate is itself a real data
  quality gate, not just a completion check.
- dbt_test_gold is itself the real verification for the Gold layer --
  a non-zero exit fails the task, exactly like running it manually.

schedule=None: manual trigger only, until a full run has been
validated end to end (see project-decisions.md / roadmap-next-steps.md
for when this becomes scheduled).

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from airflow.decorators import dag, task
from airflow.providers.databricks.operators.databricks import (
    DatabricksRunNowOperator,
)
from airflow.providers.standard.operators.bash import BashOperator

if "/opt/mdp/src" not in sys.path:
    sys.path.insert(0, "/opt/mdp/src")

ENTITIES: tuple[tuple[str, str], ...] = (
    ("customers", "marketplace.customers"),
    ("orders", "marketplace.orders"),
    ("order_items", "marketplace.order_items"),
    ("products", "marketplace.products"),
    ("payments", "marketplace.payments"),
    ("sellers", "marketplace.sellers"),
    ("categories", "marketplace.categories"),
)

DBT_PROJECT_DIR = "/opt/mdp/dbt"


@dag(
    dag_id="marketplace_batch_pipeline",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["batch", "pipeline"],
)
def marketplace_batch_pipeline():

    @task
    def extract_postgres() -> dict[str, int]:
        import psycopg
        import pyarrow.parquet as pq

        from data_platform.bootstrap import bootstrap
        from data_platform.config.settings import Settings
        from data_platform.processing.core.context_keys.storage_keys import (
            StorageKeys,
        )
        from data_platform.processing.core.execution_metadata import (
            ExecutionMetadata,
        )
        from data_platform.processing.core.execution_status import (
            ExecutionStatus,
        )
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
        from data_platform.providers.provider_factory import ProviderFactory
        from data_platform.storage.config import StorageConfig
        from data_platform.storage.models import StorageLocation

        from integrations.postgres.config import PostgresSettings

        postgres_settings = PostgresSettings()

        provider_factory = ProviderFactory(
            registry=bootstrap(),
            settings=Settings(),
        )

        storage_provider = provider_factory.create("aws.s3")

        counts: dict[str, int] = {}

        with psycopg.connect(
            host=postgres_settings.host,
            port=postgres_settings.port,
            dbname=postgres_settings.database,
            user=postgres_settings.user,
            password=postgres_settings.password,
        ) as connection:

            for entity, table_name in ENTITIES:

                with connection.cursor() as cursor:
                    cursor.execute(f"SELECT count(*) FROM {table_name}")
                    postgres_count = cursor.fetchone()[0]

                # Idempotency: clear any objects a previous run of this
                # DAG (or the one-off script) already landed, since
                # PostgresExtractionStage always appends a new file and
                # nothing downstream dedups raw/{entity}/.
                prefix = StorageLocation.from_uri(
                    f"{StorageConfig.raw(entity)}/"
                )

                for existing in storage_provider.list(prefix):
                    storage_provider.delete(existing.location)

                stage = PostgresExtractionStage(
                    id=f"extract-{entity}",
                    name=f"Extract {entity.title()}",
                    provider_name="aws.s3",
                    postgres_settings=postgres_settings,
                    table_name=table_name,
                    entity=entity,
                    provider_factory=provider_factory,
                )

                pipeline = Pipeline(
                    id=f"marketplace-batch-pipeline-extract-{entity}",
                    name=f"Postgres Extraction - {entity}",
                    stages=(stage,),
                )

                context = ProcessingContext(
                    id=f"context-extract-{entity}",
                    metadata=ExecutionMetadata(
                        execution_id=f"execution-extract-{entity}",
                    ),
                )

                result = asyncio.run(
                    SequentialExecutor().execute(pipeline, context)
                )

                if result.status != ExecutionStatus.COMPLETED:
                    stage_result = result.stage_results[0]
                    raise RuntimeError(
                        f"Extraction failed for '{entity}': "
                        f"{stage_result.error_type} - "
                        f"{stage_result.error_message}"
                    )

                uri = context.get(StorageKeys.URI)
                landed_location = StorageLocation.from_uri(uri)

                with tempfile.TemporaryDirectory() as tmp_dir:
                    local_path = Path(tmp_dir) / "landed.parquet"
                    storage_provider.download(landed_location, local_path)
                    landed_count = pq.ParquetFile(local_path).metadata.num_rows

                if landed_count != postgres_count:
                    raise RuntimeError(
                        f"Row count mismatch for '{entity}': Postgres has "
                        f"{postgres_count}, landed parquet ({uri}) has "
                        f"{landed_count}."
                    )

                counts[entity] = postgres_count

                print(f"OK: '{entity}' -- {postgres_count} rows, verified.")

        return counts

    @task
    def entities_parameter(counts: dict[str, int]) -> str:
        return ",".join(counts.keys())

    run_full_pipeline = DatabricksRunNowOperator(
        task_id="run_databricks_full_pipeline",
        databricks_conn_id="databricks_default",
        job_name="Full Pipeline",
        job_parameters={
            "entities": entities_parameter(extract_postgres()),
        },
    )

    dbt_run_gold = BashOperator(
        task_id="dbt_run_gold",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt run --select gold",
    )

    dbt_test_gold = BashOperator(
        task_id="dbt_test_gold",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt test --select gold",
    )

    run_full_pipeline >> dbt_run_gold >> dbt_test_gold


marketplace_batch_pipeline()
