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

schedule=None: reverted back from schedule=timedelta(minutes=30) --
the original justification ("manual trigger only, until a full run has
been validated end to end") was satisfied and the DAG ran on a 30-minute
schedule for real, but that schedule was itself the dominant driver of
a real AWS AWSDataTransfer cost spike with no matching freshness need
(this is a portfolio/study project, run manually when demonstrating or
testing, not a production feed with real consumers). See
docs/architecture/roadmap-next-steps.md for the full decision record
and its "Update" appending this reversal. catchup=False (unchanged)
still means no retroactive runs if a schedule is ever reintroduced.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import asyncio
import os
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

# dbt needs real write access to Athena (mdp-athena-dbt-dev workgroup),
# Glue (read mdp_silver_dev, write mdp_gold_dev) and S3 (read silver/,
# write gold/) to build Gold -- deliberately out of scope for
# mdp-airflow-ingest-dev (Terraform module.airflow_ingest), which only
# covers extract_postgres's raw/ access and CloudWatch remote logging.
# mdp-dbt-gold-dev (Terraform module.dbt_gold, environments/dev/
# security.tf) is scoped to exactly that -- Athena mdp-athena-dbt-dev,
# Glue read mdp_silver_dev / write mdp_gold_dev, S3 read silver/ +
# read-write gold/, derived from what `dbt run`/`dbt test` actually do,
# not assumed. Overriding just these two env vars (append_env=True
# merges rather than replaces the container's environment) keeps this
# scoped to exactly the two tasks that need it -- the personal key
# (MDP_PERSONAL_ACCESS_KEY_ID/SECRET) is no longer read by any DAG task,
# see docs/architecture/roadmap-next-steps.md.
DBT_AWS_CREDENTIALS: dict[str, str] = {
    "AWS_ACCESS_KEY_ID": os.environ["MDP_DBT_GOLD_ACCESS_KEY_ID"],
    "AWS_SECRET_ACCESS_KEY": os.environ["MDP_DBT_GOLD_SECRET_ACCESS_KEY"],
}


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
        from data_platform.processing.core.execution_metadata import (
            ExecutionMetadata,
        )
        from data_platform.processing.core.pipeline import Pipeline
        from data_platform.processing.core.processing_context import (
            ProcessingContext,
        )
        from data_platform.processing.executor.parallel_executor import (
            ParallelExecutor,
        )
        from data_platform.processing.extraction.postgres_extraction_stage import (
            PostgresExtractionStage,
        )
        from data_platform.observability.logging_config import (
            configure_logging,
        )
        from data_platform.processing.logging.logging_hook import LoggingHook
        from data_platform.processing.metrics.prometheus_metrics_hook import (
            PrometheusHook,
        )
        from data_platform.processing.tracing.tracing_hook import TracingHook
        from data_platform.providers.provider_factory import ProviderFactory
        from data_platform.storage.config import StorageConfig
        from data_platform.storage.models import StorageLocation

        from integrations.postgres.config import PostgresSettings

        configure_logging()

        postgres_settings = PostgresSettings()

        provider_factory = ProviderFactory(
            registry=bootstrap(),
            settings=Settings(),
        )

        storage_provider = provider_factory.create("aws.s3")

        # One PrometheusHook shared across every entity in this task
        # run, so all of them land in the same CollectorRegistry and
        # are pushed to the Pushgateway together, as a single batch,
        # once the run is done -- see run_postgres_extraction_once.py
        # for the same pattern.
        metrics_hook = PrometheusHook()

        postgres_counts: dict[str, int] = {}

        stage_by_entity: dict[str, PostgresExtractionStage] = {}

        # Pre-pass, sequential and cheap (a count query + an idempotency
        # list/delete per entity -- not the extraction itself): builds
        # every Stage and captures each entity's real Postgres row
        # count for the post-run verification below, before any of the
        # 7 extractions actually runs concurrently.
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
                    postgres_counts[entity] = cursor.fetchone()[0]

                # Idempotency: clear any objects a previous run of this
                # DAG (or the one-off script) already landed, since
                # PostgresExtractionStage always appends a new file and
                # nothing downstream dedups raw/{entity}/.
                prefix = StorageLocation.from_uri(
                    f"{StorageConfig.raw(entity)}/"
                )

                for existing in storage_provider.list(prefix):
                    storage_provider.delete(existing.location)

                stage_by_entity[entity] = PostgresExtractionStage(
                    id=f"extract-{entity}",
                    name=f"Extract {entity.title()}",
                    provider_name="aws.s3",
                    postgres_settings=postgres_settings,
                    table_name=table_name,
                    entity=entity,
                    provider_factory=provider_factory,
                )

        # All 7 extractions as a single parallel group: independent by
        # construction (each reads its own Postgres table, writes its
        # own raw/{entity}/ object, and returns its landed location on
        # StageResult.output rather than through a ContextWriter -- see
        # ParallelExecutor's and PostgresExtractionStage's docstrings
        # for why that distinction matters under real concurrency).
        pipeline = Pipeline(
            id="marketplace-batch-pipeline-extract-postgres",
            name="Postgres Extraction",
            stages=(tuple(stage_by_entity[entity] for entity, _ in ENTITIES),),
        )

        context = ProcessingContext(
            id="context-extract-postgres",
            metadata=ExecutionMetadata(
                execution_id="execution-extract-postgres",
            ),
        )

        executor = ParallelExecutor()
        executor.register_hooks(LoggingHook())
        executor.register_hooks(TracingHook())
        executor.register_hooks(metrics_hook)

        result = asyncio.run(
            executor.execute(pipeline, context)
        )

        results_by_entity = {
            stage.entity: next(
                (
                    stage_result
                    for stage_result in result.stage_results
                    if stage_result.stage_id == stage.id
                ),
                None,
            )
            for stage in stage_by_entity.values()
        }

        failed_or_missing = {
            entity: stage_result
            for entity, stage_result in results_by_entity.items()
            if stage_result is None or stage_result.failed
        }

        if failed_or_missing:
            details = "; ".join(
                f"{entity}: did not complete (pipeline-level failure)"
                if stage_result is None
                else f"{entity}: {stage_result.error_type} - "
                f"{stage_result.error_message}"
                for entity, stage_result in failed_or_missing.items()
            )
            raise RuntimeError(f"Extraction failed for: {details}")

        counts: dict[str, int] = {}

        for entity, stage_result in results_by_entity.items():
            uri = stage_result.output["uri"]
            landed_location = StorageLocation.from_uri(uri)

            with tempfile.TemporaryDirectory() as tmp_dir:
                local_path = Path(tmp_dir) / "landed.parquet"
                storage_provider.download(landed_location, local_path)
                landed_count = pq.ParquetFile(local_path).metadata.num_rows

            postgres_count = postgres_counts[entity]

            if landed_count != postgres_count:
                raise RuntimeError(
                    f"Row count mismatch for '{entity}': Postgres has "
                    f"{postgres_count}, landed parquet ({uri}) has "
                    f"{landed_count}."
                )

            counts[entity] = postgres_count

            print(f"OK: '{entity}' -- {postgres_count} rows, verified.")

        metrics_hook.push(job="extract_postgres")

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

    @task
    def ship_databricks_run_logs() -> int:
        """
        Sprint 13 close-out: ships the real "Full Pipeline" run's task
        output (bronze, bronze_validate, bronze_optimize, silver) to
        the databricks CloudWatch log group. Parallel to dbt_run_gold,
        not upstream of it -- a shipping failure here must never block
        the real Gold build (see
        integrations/databricks/observability/run_output_shipper.py's
        own docstring for what's actually shippable from these jobs --
        serverless compute, no cluster_log_conf, so notebook output via
        the Jobs API's get-run-output is the only reachable signal).

        Builds its own WorkspaceClient from the databricks_default
        Connection's host/token (the same PAT
        DatabricksRunNowOperator already uses) -- deliberately not
        DatabricksContext.workspace, which resolves
        ~/.databrickscfg's `modern-data-platform` profile (expired,
        wrong auth mechanism for this container regardless -- see
        docs/environment-inventory.md).
        """
        from airflow.hooks.base import BaseHook
        from airflow.sdk import get_current_context
        from databricks.sdk import WorkspaceClient

        from integrations.databricks.observability.run_output_shipper import (
            ship_run_output_to_cloudwatch,
        )

        context = get_current_context()

        run_id = context["ti"].xcom_pull(
            task_ids="run_databricks_full_pipeline", key="run_id"
        )

        if run_id is None:
            raise RuntimeError(
                "run_databricks_full_pipeline did not push a run_id XCom -- "
                "cannot ship its output to CloudWatch."
            )

        connection = BaseHook.get_connection("databricks_default")

        workspace = WorkspaceClient(
            host=connection.host,
            token=connection.password,
        )

        shipped = ship_run_output_to_cloudwatch(
            workspace=workspace,
            run_id=run_id,
            log_group_name=os.environ["DATABRICKS_CLOUDWATCH_LOG_GROUP"],
        )

        print(f"OK: shipped {shipped} Databricks task outputs to CloudWatch.")

        return shipped

    dbt_run_gold = BashOperator(
        task_id="dbt_run_gold",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt run --select gold",
        env=DBT_AWS_CREDENTIALS,
        append_env=True,
    )

    dbt_test_gold = BashOperator(
        task_id="dbt_test_gold",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt test --select gold",
        env=DBT_AWS_CREDENTIALS,
        append_env=True,
    )

    run_full_pipeline >> dbt_run_gold >> dbt_test_gold
    run_full_pipeline >> ship_databricks_run_logs()


marketplace_batch_pipeline()
