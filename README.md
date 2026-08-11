# Modern Data Platform

<p align="center">

**A cloud-agnostic, event-driven Modern Data Platform built with open-source technologies and production-ready engineering practices.**

Design and implementation inspired by real-world enterprise data platforms.

</p>

---

## Overview

Modern Data Platform is an end-to-end Data Engineering project designed to demonstrate how production-grade data platforms are built.

The project covers the complete lifecycle of modern analytical data:

- Change Data Capture (CDC)
- Event Streaming
- Distributed Processing
- Lakehouse Architecture
- Data Modeling
- Infrastructure as Code
- Observability
- CI/CD

Rather than focusing on a single technology, this project emphasizes software engineering principles, modular architecture, and cloud portability.

---

# Architecture Goals

The platform was designed around a few fundamental principles.

- Cloud-agnostic architecture
- Event-driven communication
- Infrastructure as Code
- Modular design
- Provider-based abstractions
- Reproducible environments
- High testability
- Production-ready practices

More details are available in the Architecture Decision Records (ADRs).

---

# High-Level Architecture

```text
                 Source Systems
                        │
                        ▼
                 PostgreSQL
                        │
                        ▼
                 Debezium (CDC)
                        │
                        ▼
                  Apache Kafka
                        │
                        ▼
                Apache Airflow
                        │
                        ▼
              Platform Abstractions
                        │
        ┌───────────────┼────────────────┐
        ▼               ▼                ▼
    Storage         Compute         Messaging
        │               │                │
        ▼               ▼                ▼
      Amazon S3     Databricks       Kafka/MSK
                        │
                        ▼
                 Apache Spark
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
           Bronze               Silver
         (Delta Lake)         (Delta Lake)
                                   │
                                   ▼
                            Glue Catalog
                                   │
                                   ▼
                                  dbt
                                   │
                                   ▼
                                 Gold
                                   │
                                   ▼
                            Amazon Athena
                          ┌────────┴─────────┐
                          ▼                  ▼
                       Metabase           Power BI
```

Databricks/Spark's responsibility ends at Silver; Gold is dbt's
responsibility, reading Silver through the Glue Catalog (see
ADR-011).

---

# Technology Stack

| Layer | Technology |
|--------|------------|
| Programming Language | Python 3.12 |
| Structured Logging | structlog |
| Database | PostgreSQL |
| CDC | Debezium |
| Streaming | Apache Kafka |
| Workflow Orchestration | Apache Airflow |
| Distributed Processing | Apache Spark |
| Compute Platform | Databricks |
| Data Access / Governance | Unity Catalog (Storage Credential + External Location) |
| Object Storage | Amazon S3 |
| Table Format | Delta Lake |
| Data Modeling | dbt |
| Query Engine | Amazon Athena |
| Visualization | Metabase (containerized), Power BI |
| Infrastructure as Code | Terraform |
| Containers | Docker |
| Version Control | GitHub |

---

# Project Structure

```text
modern-data-platform/

├── docs/
│   └── architecture/
│
├── infrastructure/
│   ├── terraform/
│   ├── docker/
│   └── databricks/
│
├── src/
│   ├── common/
│   ├── data_platform/
│   │   ├── catalog/
│   │   ├── compute/
│   │   ├── config/
│   │   ├── contracts/
│   │   ├── datalake/
│   │   ├── enums/
│   │   ├── exceptions/
│   │   ├── http/
│   │   ├── identity/
│   │   ├── messaging/
│   │   ├── models/
│   │   ├── monitoring/
│   │   ├── notifications/
│   │   ├── observability/
│   │   ├── processing/
│   │   ├── providers/
│   │   ├── security/
│   │   ├── storage/
│   │   ├── types/
│   │   └── workflow/
│   ├── integrations/
│   ├── quality/
│   ├── simulator/
│   └── streaming/
│
├── airflow/
├── alembic/
├── dbt/
├── notebooks/
├── scripts/
└── tests/
```

---

# Repository Modules

## Platform

Infrastructure-independent abstractions.

Examples:

- Storage
- Compute
- Messaging
- Monitoring
- Catalog
- Security

---

## Cloud

Provider implementations.

Examples:

- AWS
- Azure
- Google Cloud
- Local

---

## Ingestion

Responsible for collecting data from external systems.

Examples:

- CDC
- APIs
- Batch Files

---

## Streaming

Responsible for asynchronous communication.

Examples:

- Kafka Producers
- Kafka Consumers
- Event Serialization

---

## Processing

Responsible for distributed processing.

Examples:

- Bronze Layer
- Silver Layer

Gold modeling is dbt's responsibility, not Spark's (see ADR-011) --
Databricks/Spark's processing responsibility ends at Silver.

---

## Quality

Responsible for validating data quality.

Future integrations include:

- Great Expectations
- Custom Validators

---

## Orchestration

Workflow management using Apache Airflow.

---

## Analytics

Analytical assets and semantic models.

---

# Data Flow

```text
Simulator

↓

PostgreSQL

↓

Debezium

↓

Kafka

↓

Airflow

↓

S3

↓

Spark

↓

Bronze

↓

Silver

↓

Glue Catalog

↓

dbt

↓

Gold

↓

Athena

↓

Power BI
```

---

# Cloud Strategy

The platform follows a capability-based architecture.

Business logic never depends directly on cloud providers.

| Capability | AWS | Azure | GCP |
|------------|-----|--------|-----|
| Storage | S3 | ADLS Gen2 | GCS |
| Compute | Databricks / EMR | Databricks / Synapse | Databricks / Dataproc |
| Messaging | Kafka / MSK | Event Hubs | Pub/Sub |
| Monitoring | CloudWatch | Azure Monitor | Cloud Monitoring |
| Secrets | Secrets Manager | Key Vault | Secret Manager |

Provider-specific implementations are isolated behind platform contracts.

---

# Development Principles

- Infrastructure as Code
- Cloud Agnostic
- Provider Pattern
- Layered Architecture
- Dependency Injection
- Type Safety
- Automated Testing
- Continuous Integration

---

# Quick Start

## Clone the repository

```bash
git clone https://github.com/your-user/modern-data-platform.git

cd modern-data-platform
```

## Install dependencies

```bash
uv sync --all-extras
```

`--all-extras` pulls in `orchestration`/`warehouse`/`streaming`
(Airflow, dbt, confluent-kafka) alongside the core dependencies --
split out of `[project.dependencies]` so the Databricks notebooks'
wheel install (`uv build --wheel`, `infrastructure/databricks/
databricks.yml`) doesn't pull in Airflow's/dbt's/Kafka's dependency
trees, none of which those notebooks import. Local dev needs all of
it; plain `uv sync` (no `--all-extras`) now leaves those three out.

## Start local infrastructure

```bash
docker compose up -d
```

The local environment includes:

- PostgreSQL (marketplace database + Airflow metastore)
- Kafka (+ Kafka UI)
- Debezium
- Airflow
- Redis (Celery broker for Airflow)
- Bronze Consumer (containerized, see "Run the Bronze Consumer" below)
- Prometheus + Grafana + Pushgateway + statsd-exporter (see "Phase 6 — Observability")

## Apply database migrations

```bash
uv run alembic upgrade head
```

The `marketplace` schema's initial 17 tables come from
`infrastructure/docker/postgres/init/*.sql`, run automatically by
Postgres on first container boot -- Alembic (`alembic/`, `alembic.ini`
at the repo root) takes over from there for every change after that,
over `postgresql+psycopg://` (psycopg v3), the same driver as the rest
of the app.

## Run the simulator

```bash
PYTHONUNBUFFERED=1 uv run python -m simulator.app > /tmp/simulator.log 2>&1 &
```

`pyproject.toml` now has a real `[build-system]` (hatchling,
`[tool.hatch.build.targets.wheel]` listing every real `src/` package),
so `uv sync` installs the project itself in editable mode and every
`src/` package (`simulator` included) is importable without
`PYTHONPATH` -- confirmed live: every package imports cleanly with
`PYTHONPATH` unset, and `pytest`'s own `pythonpath = ["src"]` override
(no longer needed either) was dropped. See "`src/` packages aren't
installable -- `PYTHONPATH` required outside pytest" in
`docs/architecture/roadmap-next-steps.md` for the history of this gap.

An unhandled exception still kills the process (there is no top-level
retry/supervisor loop), matching the exit code you'll see if it dies.
Faker-uniqueness exhaustion and cross-run unique-constraint collisions
are handled (`unique_or_fallback`, `insert_with_unique_retry`), so
those specific cases no longer crash the process -- but any other
unexpected failure (e.g. Postgres becoming unreachable) still will.
Run it with `PYTHONUNBUFFERED=1` (or `python -u`): Python
block-buffers stdout when it isn't a TTY, so without this a crash can
lose its own traceback in an unflushed buffer, leaving the log looking
like it died silently mid-line with no error at all. This doesn't fix
the underlying failure -- it just guarantees you can see why it
failed.

## Run the Bronze Consumer

Runs as its own container (`bronze-consumer`, `infrastructure/docker/streaming/Dockerfile`)
as part of `docker compose up -d` -- no separate step needed. It's a
plain `python:3.12-slim` image with the project's own dependencies
installed via `uv sync` from `pyproject.toml`/`uv.lock` (code `COPY`'d
in, not volume-mounted -- rebuild the image, `docker compose build
bronze-consumer`, after a `src/` change under it).

For local iteration without a rebuild, run it directly instead:

```bash
uv run python scripts/run_bronze_consumer.py
```

Long-running process: consumes Debezium change events for all 16
streaming entities directly off Kafka and writes them to their Bronze
Delta tables via `deltalake` (no Spark) -- the streaming half of
ADR-0008's flow, independent from Airflow. Stop with Ctrl+C.

Validated end to end against real Postgres/Debezium/Kafka/Delta (see
`tests/integration/kafka/test_bronze_consumer_real_kafka.py`, run with
`-m real_kafka`). This phase's known limitations -- no Dead Letter
Queue, no distributed lock against the batch flow writing the same
Bronze tables, deletes landing as regular appends rather than deletes
(the domain already soft-deletes via `deleted_at`), and a round-robin
poll loop that is throughput-bound under a large backlog (see
`docs/architecture/roadmap-next-steps.md`) -- are documented in
`src/streaming/consumers/bronze_consumer.py`'s module docstring.

Exposes Prometheus metrics on `:9200/metrics` (write duration, records
written, write failures, messages consumed, consumer lag -- see
"Phase 6 — Observability" below); the container's own AWS credentials
need `AWS_REGION`/`AWS_DEFAULT_REGION` set explicitly (unlike the rest
of the project's S3 access, which goes through boto3 --
`write_deltalake()`'s pure-Rust S3 client doesn't follow a
cross-region redirect the way boto3 does).

## Databricks authentication (local)

`DatabricksComputeProvider` delegates authentication entirely to the
official Databricks SDK credential chain (`~/.databrickscfg`,
`DATABRICKS_HOST`/`DATABRICKS_TOKEN`, Azure CLI, etc). By default it
doesn't force any profile, so it depends on either your local
`~/.databrickscfg` having a `default_profile` set, or the
`DATABRICKS_CONFIG_PROFILE` environment variable being exported in
your shell -- this project's profile is `modern-data-platform`, not
`DEFAULT`:

```bash
export DATABRICKS_CONFIG_PROFILE=modern-data-platform
```

To make the profile deterministic regardless of what your personal
`~/.databrickscfg` resolves to (e.g. on a machine/CI runner without a
`default_profile` set), pass it explicitly via `DatabricksSettings`
instead of relying on the environment:

```python
from integrations.databricks.config.databricks_settings import DatabricksSettings
from integrations.databricks.core.databricks_context import DatabricksContext

context = DatabricksContext(DatabricksSettings(profile="modern-data-platform"))
```

---

# Documentation

Architecture documentation is located in:

```text
docs/architecture/
```

Current ADRs:

- ADR-000 – Architecture Principles
- ADR-001 – Platform Architecture
- ADR-002 – Platform Contracts
- ADR-003 – Cloud Strategy
- ADR-004 – Repository Structure
- ADR-005 – Development Standards
- ADR-006 – Platform Capability Model
- ADR-007 – Workflow Capability
- ADR-0008 – Batch vs Streaming Processing Architecture
- ADR-009 – Adopt Processing Framework
- ADR-010 – Capability-Based Shared Execution Context
- ADR-011 – Gold Modeling Moves to dbt

---

# Business Intelligence

Two BI integrations against the same Gold layer over Athena, tool-agnostic by design: dbt models the star schema once (`dbt/models/gold/`), any BI tool queries it independently through Athena, none of them tied to how the other connects.

## Metabase (containerized, done)

- `metabase` + `postgres-metabase` services (`infrastructure/docker/docker-compose.yml`) -- `http://localhost:3001`.
- Authenticates as a dedicated, read-only IAM User (`mdp-bi-reader-dev`, Terraform `module.bi_reader`), not `terraform-admin` -- scoped to the Gold database/tables, the `gold/` S3 prefix, and its own dedicated Athena staging bucket.
- First real dashboard, **Gold Layer Overview** (`http://localhost:3001/dashboard/2`): total orders, orders by day, top products by revenue, top sellers by order count, average order value. Built via the Metabase API using Native Query (SQL), not the visual builder, so every question is versioned as plain text instead of living only in Metabase's own metadata database -- see `dashboards/metabase/` (SQL sources, data-cardinality caveats, and a from-scratch recreation procedure, since Metabase's Serialization/export feature is Pro-only).

## Power BI (planned, not yet connected)

Investigated but not implemented yet. Connects to the same `mdp-bi-reader-dev` IAM User and `mdp-athena-dev` workgroup as Metabase -- no new IAM identity needed when this gets built, by design (both BI tools share one read-only access boundary). Standard path: the official AWS Athena ODBC driver, a DSN, Power BI Desktop (Import mode) validated against `fact_orders`/`dim_customers`/`dim_products` before considering Power BI Service + an On-premises Data Gateway for scheduled refresh. See `docs/architecture/roadmap-next-steps.md` for the full investigation and remaining steps.

---

# Project Roadmap

Status legend: ✅ Done — 🔶 Partial — ⬜ Not started.

## Phase 1 — Foundation

- ✅ Repository Structure
- ✅ Docker Environment (Postgres, Kafka, Debezium, Airflow, Redis)
- ✅ Terraform Foundation (`dev` environment applied: S3, Glue databases, Athena workgroup, Unity Catalog IAM trust). **`terraform init` alone is no longer enough** as of this session: `backend.tf` (in both `infrastructure/terraform/bootstrap/` and `infrastructure/terraform/environments/dev/`) is now an empty `backend "s3" {}` block -- Terraform's own backend blocks can't reference `var.*` (a hard restriction, not a choice), so the real bucket/key/region moved to a sibling `backend-dev.hcl` file, passed explicitly:
  ```bash
  terraform init -backend-config=backend-dev.hcl
  ```
  Deliberate, not a regression -- see `docs/architecture/roadmap-next-steps.md` for why, and for the real `terraform state list`/`plan` validation that this reconfiguration didn't touch any existing state (same bucket/key/region as the hardcoded values it replaced, recognized as the same backend, no migration).

## Phase 2 — CDC

- ✅ PostgreSQL (populated by the simulator)
- ✅ Debezium (connector running, capturing all `marketplace` tables)
- ✅ Kafka (broker up, topics created on first captured change)
- ✅ Bronze Consumer: continuous Kafka consumer streaming Debezium CDC events straight into Bronze Delta tables via `deltalake` (no Spark), independent from Airflow (see ADR-0008), validated end to end against real Postgres/Debezium/Kafka (`-m real_kafka`)
- ✅ Real Airflow DAG (`marketplace_batch_pipeline`, Airflow 3.3.0) orchestrating the pipeline end to end -- Postgres extraction (7 entities) -> Databricks `full_pipeline` -> `dbt run`/`dbt test --select gold`, validated with a real manual trigger against real Postgres/S3/Databricks/Athena. Scheduled every 30 minutes (`schedule=timedelta(minutes=30)`, was `schedule=None` pending this exact validation) as of this session.

## Phase 3 — Data Lake

- ✅ Postgres extraction → `raw/` → Bronze → Silver, validated end to end against real Postgres/S3/Databricks for 7 entities (customers, orders, order_items, products, payments, sellers, categories)
- ✅ Silver registered in the Glue Catalog (`SilverCatalogRegistrationStage`)
- Gold is no longer a Spark/Databricks stage here -- moved to dbt (see ADR-011 and Phase 4)
- ✅ Bronze split into two physical tables: `bronze/{entity}` (streaming, `bronze_consumer.py`, Kafka/Debezium, all 16 entities) and `bronze_batch/{entity}` (batch, `ingest_sources.ipynb`/`validate_bronze.ipynb`/`optimize_bronze.ipynb`/`transform_silver.ipynb`, the 7 dbt/Gold entities) -- `StorageConfig.bronze_batch()`. Both used to share one path, which let the streaming consumer's continuous `append`s and the batch flow's periodic `overwrite`s land inconsistent row versions in Silver for any entity that receives an update (found live: 139 duplicate `product_id` rows in `stg_products`, root-caused all the way to Postgres, Bronze's real `_delta_log` history, and the Debezium decoder before fixing). Validated live: real "Full Pipeline" run + `dbt test --select gold` **28/28 passing** (was 24/28). See `docs/architecture/roadmap-next-steps.md`.
- ✅ Postgres extraction parallelized: `Pipeline` (`data_platform/processing/core/pipeline.py`) gained `StageGroup` -- a nested `tuple[Stage, ...]` inside `Pipeline.stages` is a group of Stages that run concurrently via `asyncio.gather`; groups still execute in sequence relative to each other. A new `ParallelExecutor(BaseExecutor)` (`data_platform/processing/executor/parallel_executor.py`) runs them; `SequentialExecutor` needed no changes at all -- flat iteration (`for stage in pipeline`) auto-flattens groups, so it still runs every stage one at a time, in order, exactly as before. `ExecutionRuntime`'s per-stage state (current stage/attempt, last result, last exception) moved from single `ProcessingContext` keys to `contextvars.ContextVar` -- each concurrent stage's own `asyncio.Task` gets an isolated copy, so two stages in the same group can no longer race on shared state the way the old single-slot design did. `StageResult` gained an `output: dict[str, Any]` field so a Stage can return its own result directly (e.g. `PostgresExtractionStage`'s landed `uri`/`bucket`/`object_key`) instead of publishing it into the shared `ProcessingContext` via a `ContextWriter`, which would collide the same way under real concurrency. `extract_postgres`'s 7 entities now run as a single parallel group (previously 7 separate sequential `Pipeline` runs) -- validated live: 45.0s → 32.2s (~1.4x), more modest than the ~2.46x theoretical estimate, since Python's GIL limits how much of the CPU-bound part (Arrow table construction, Parquet serialization) actually overlaps inside `asyncio.to_thread()` -- only the real I/O (the Postgres query, the S3 upload) genuinely does. `PostgresExtractionStage.execute()` itself needed that `asyncio.to_thread()` wrapper added: psycopg/boto3 are blocking clients, so without it the coroutine had no real `await` point for `asyncio.gather()` to interleave at, and the first live validation ran the 7 stages one at a time regardless (71s, worse than sequential) -- caught only by measuring the real run, not by the design or the unit tests (see commit `1f3002b`).

## Phase 4 — Data Modeling

- ✅ dbt project scaffolded (`dbt/`), real connection to Athena/Glue confirmed (`dbt debug`)
- ✅ Silver sources declared for all 7 entities; `stg_*` staging models implemented and tested against real Athena data for all 7
- ✅ `int_`/`dim_`/`fact_` Gold models: `int_order_items_enriched`, `dim_customers`, `dim_products`, `fact_orders` (star schema, table-materialized, `fact_orders` partitioned by `order_year`/`order_month`) -- `dbt run`/`dbt test` both green against real Athena
- ✅ Gold `table`-materialized models land under a real, predictable `gold/{schema}/{table}/` S3 path (`external_location`, set explicitly per model) via a dedicated Athena workgroup for dbt builds (`mdp-athena-dbt-dev`, `enforce_output_location=false`), separate from the ad-hoc/BI workgroup (`mdp-athena-dev`, untouched). Found live: `mdp-athena-dev`'s `enforce_workgroup_configuration=true` makes dbt-athena's CTAS macro drop any location clause for Hive tables regardless of `external_location`/`s3_data_dir` config -- Gold tables were silently landing under a random `{uuid}` path instead. See `docs/architecture/roadmap-next-steps.md`.
- ⬜ Metrics layer

## Phase 5 — Analytics

- 🔶 Dashboards -- **Sprint 12 (BI) partially complete: Metabase done (dashboard built), Power BI connected (dashboard pending).** Metabase (containerized, `infrastructure/docker/docker-compose.yml`) connected to Gold over Athena end to end. Authenticates as a dedicated, read-only IAM User (`mdp-bi-reader-dev`, Terraform `module.bi_reader`) scoped to the Gold database/tables, the `gold/` S3 prefix, and its own dedicated staging bucket -- not `terraform-admin`. First real dashboard built via the Metabase API (Native Query/SQL, not the visual builder, so it stays versionable): **[Gold Layer Overview](dashboards/metabase/README.md)** -- total orders, orders by day, top products by revenue, top sellers by order count, average order value; SQL sources and data-cardinality caveats in `dashboards/metabase/`. Power BI Desktop connected and validated the same way (ODBC driver + DSN, `mdp-bi-reader-dev` reused, same `mdp-athena-dev` workgroup) -- real rows confirmed for `dim_customers`/`dim_products`/`fact_orders`; no dashboard built yet. See `docs/architecture/roadmap-next-steps.md` for the connection details, including two real issues hit and fixed along the way (a Store-app ODBC DSN-visibility bug, a driver checksum-validation bug).
- ⬜ Business KPIs

## Phase 6 — Observability

- ✅ Logging: `structlog` adopted for structured JSON logging, replacing bare `logging.getLogger` -- unified across the processing framework (`ConsoleLogger`/`ConsoleTracer`, plugged into `SequentialExecutor` via `LoggingHook`/`TracingHook`) and streaming (`data_platform.monitoring.logger.get_logger`). A single `configure_logging()` bootstrap (`data_platform/observability/logging_config.py`) is called at every real entry point (Airflow DAG task, one-off scripts, Bronze Consumer, Airflow bootstrap script), validated live against real Airflow task logs and the real Bronze Consumer. Airflow's own task logs ship to the real `/mdp/dev/airflow` CloudWatch Log Group (`CloudwatchTaskHandler`, `AIRFLOW__LOGGING__REMOTE_*` in `docker-compose.yml`, ARN kept out of code via `AIRFLOW_CLOUDWATCH_LOG_GROUP_ARN` in `.env`), in parallel with the local files under `/opt/airflow/logs`. **Sprint 13 close-out, part 1**: of the other 5 CloudWatch log groups, `glue`/`athena` turned out to have zero possible producer in this stack (confirmed against AWS's own docs, not assumed) and were removed from Terraform as dead infrastructure; `platform` (this project's own structlog JSON, via an additive CloudWatch processor in `configure_logging()`) and `databricks` (a new Airflow task shipping the real "Full Pipeline" run's task output, event-driven, not polled) are now wired and validated live end to end (`aws logs get-log-events` against real events); `terraform` is wired via an optional wrapper script (`scripts/terraform_with_cloudwatch_logging.py`), also validated live. See `docs/architecture/roadmap-next-steps.md` for the full design decisions (including two real bugs found and fixed along the way: a stale manually-mirrored dependency list in the Airflow image, and a missing `AWS_REGION` in the Airflow containers).
- ✅ Metrics: `MetricsHook`/`StatisticsHook` (dead code -- an in-process, home-grown registry never scraped by anything) replaced by real `prometheus_client` instrumentation across 3 sources, all scraped by a real Prometheus (`infrastructure/docker/monitoring/prometheus/prometheus.yml`, `scrape_interval: 15s`):
  - **Processing framework**: `PrometheusHook` (`data_platform/processing/metrics/prometheus_metrics_hook.py`, same shape as `LoggingHook`/`TracingHook`) emits `mdp_pipeline_duration_seconds`, `mdp_stage_duration_seconds`, `mdp_stage_executions_total` and `mdp_pipeline_last_run_timestamp_seconds`, registered in all 3 real entry points (`extract_postgres` DAG task, `run_postgres_extraction_once.py`, `run_silver_catalog_registration_once.py`) and pushed to a real Pushgateway (`PrometheusHook.push(job=...)`) once each run finishes -- these are short-lived processes, not something Prometheus can scrape directly. Validated live: a real `extract_postgres` run (7 entities) landed real per-entity duration/status series in the Pushgateway under `job="extract_postgres"`, scraped by Prometheus with `honor_labels: true` so the pushed `job` label survives instead of being overwritten.
  - **Airflow**: native metrics via `AIRFLOW__METRICS__STATSD_ON` -> `statsd-exporter` (mapping config: `monitoring/statsd-exporter/mapping.yml`, covering dagrun/task duration, task finish state, pool slots, scheduler heartbeat). Validated live: real `airflow_pool_*` and `airflow_scheduler_heartbeat_total` series observed at `statsd-exporter:9102/metrics`, correctly labeled (not baked into the metric name).
  - **Bronze Consumer**: module-level metrics (`mdp_bronze_write_duration_seconds`, `mdp_bronze_records_written_total`, `mdp_bronze_write_failures_total`, `mdp_bronze_messages_consumed_total`, `mdp_bronze_consumer_lag`) exposed on `:9200/metrics`, scraped directly (it's long-running, unlike the two sources above). `mdp_bronze_consumer_lag` required extending `MessagingProvider` with `consumer_lag(topic, group_id)` (implemented in `KafkaMessagingProvider` via `assignment()`/`position()`/`get_watermark_offsets()`). Validated live against a real historical backlog (see `docs/architecture/roadmap-next-steps.md` for the throughput limitation this surfaced).
  - Grafana provisions the Prometheus datasource automatically (`monitoring/grafana/provisioning/datasources/prometheus.yml`) -- validated live via `/api/datasources/{uid}/health` ("Successfully queried the Prometheus API"). **Sprint 13 close-out, part 2**: first real dashboard, **Pipeline Health** (`/d/mdp-pipeline-health`), provisioned as JSON (`monitoring/grafana/provisioning/dashboards/`, `allowUiUpdates: false`), same config-as-code discipline as the Metabase dashboard. 11 panels across all 3 metric sources above -- every PromQL query confirmed against real metric/label names live (Prometheus HTTP API) before being written into the dashboard, not guessed from the instrumentation code. Validated live end to end via Grafana's own `/api/ds/query` (not just Prometheus directly): real labeled data returned for both an Airflow panel and a Bronze Consumer panel.
- ✅ Alerts: **Sprint 13 close-out, part 3 (final)**. 4 rules provisioned as code (`monitoring/grafana/provisioning/alerting/`), one per signal already on the Pipeline Health dashboard -- pipeline staleness, Airflow scheduler heartbeat stalled, Bronze Consumer write failures, Airflow task failures. Validated live via the Grafana alerting API: all 4 show `health: ok`, no `lastError`, correct `inactive` state matching real current conditions. Deliberate, documented scope limit: this dev environment has no real notification channel (no SMTP/Slack/webhook anywhere in `docker-compose.yml`/`.env`) -- the contact point points at `localhost:1` (nothing listens there) rather than faking a working one. Rule *evaluation* is real and validated; notification *delivery* is not, and is tracked as remaining work, not silently skipped.

## Phase 7 — CI/CD

- ⬜ GitHub Actions
- ⬜ Automated Testing (tests exist and run locally; not yet wired into CI)
- ⬜ Deployment

---

# Future Improvements

Planned enhancements include:

- Azure implementation
- Google Cloud implementation
- Apache Iceberg
- OpenLineage
- DataHub
- Kubernetes deployment
- Feature Store
- Machine Learning pipelines

---

# Contributing

Contributions are welcome. There is no separate `CONTRIBUTING.md` yet
-- this section is the contributing guideline until one exists.

## Keeping the README in sync with the architecture

Any structural architecture change must update this README in the
same commit, or in a commit immediately following it -- divergence
between this document and the real state of the project should never
be allowed to accumulate. This applies to changes such as:

- A data format or table format change (e.g. adopting/dropping Delta Lake, Iceberg)
- A catalog or query engine change (e.g. Glue/Athena replaced or supplemented)
- A new capability or integration (e.g. a new cloud provider, a new messaging system)
- A Project Roadmap phase moving from not-started to partial/done, or vice versa

When in doubt about whether a change is "structural" enough to require this, err on the side of updating the README.

---

# License

This project is licensed under the MIT License.

See the LICENSE file for details.

---

# Acknowledgements

This project was inspired by modern data engineering practices and the architecture of enterprise-grade data platforms.

Special thanks to the open-source community behind:

- Apache Airflow
- Apache Kafka
- Apache Spark
- dbt
- Terraform
- Docker
- Debezium