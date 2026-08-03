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
                                   │
                                   ▼
                              Power BI
```

Databricks/Spark's responsibility ends at Silver; Gold is dbt's
responsibility, reading Silver through the Glue Catalog (see
ADR-011).

---

# Technology Stack

| Layer | Technology |
|--------|------------|
| Programming Language | Python 3.12 |
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
| Visualization | Power BI |
| Infrastructure as Code | Terraform |
| Containers | Docker |
| Version Control | GitHub |

---

# Project Structure

```text
modern-data-platform/

├── docs/
│   ├── architecture/
│   ├── diagrams/
│   ├── guides/
│   └── roadmap/
│
├── infrastructure/
│   ├── terraform/
│   └── environments/
│
├── src/
│   ├── analytics/
│   ├── cloud/
│   ├── common/
│   ├── ingestion/
│   ├── orchestration/
│   ├── platform/
│   ├── processing/
│   ├── quality/
│   └── streaming/
│
├── simulator/
├── notebooks/
├── dbt/
├── docker/
├── tests/
└── scripts/
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
uv sync
```

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

## Apply database migrations

```bash
PYTHONPATH=src uv run alembic upgrade head
```

The `marketplace` schema's initial 17 tables come from
`infrastructure/docker/postgres/init/*.sql`, run automatically by
Postgres on first container boot -- Alembic (`alembic/`, `alembic.ini`
at the repo root) takes over from there for every change after that.
Alembic uses `postgresql+psycopg2://` here, not the app's usual
psycopg v3 -- `apache-airflow-core` pins SQLAlchemy below 2.0, which has
no v3 dialect (see `docs/architecture/roadmap-next-steps.md`'s Airflow
upgrade entry for why, and when that goes away).

## Run the simulator

```bash
PYTHONPATH=src PYTHONUNBUFFERED=1 uv run python -m simulator.app > /tmp/simulator.log 2>&1 &
```

`PYTHONPATH=src` is required: `pyproject.toml` has no `[build-system]`,
so `uv run` does not install `simulator` (or any other `src/` package)
into the venv -- without it you get `ModuleNotFoundError: No module
named 'simulator'`. `pytest` doesn't need this because
`[tool.pytest.ini_options]` already sets `pythonpath = ["src"]`, but
that config only applies to pytest, not to `uv run`/plain `python`.
See "`src/` packages aren't installable -- `PYTHONPATH` required
outside pytest" in `docs/architecture/roadmap-next-steps.md` for the
alternative of making the project properly installable instead of
relying on `PYTHONPATH`.

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

# Project Roadmap

Status legend: ✅ Done — 🔶 Partial — ⬜ Not started.

## Phase 1 — Foundation

- ✅ Repository Structure
- ✅ Docker Environment (Postgres, Kafka, Debezium, Airflow, Redis)
- ✅ Terraform Foundation (`dev` environment applied: S3, Glue databases, Athena workgroup, Unity Catalog IAM trust)

## Phase 2 — CDC

- ✅ PostgreSQL (populated by the simulator)
- ✅ Debezium (connector running, capturing all `marketplace` tables)
- ✅ Kafka (broker up, topics created on first captured change)
- ⬜ Continuous Kafka consumer feeding the pipeline (messaging capability exists and is tested; no long-running consumer loop yet)
- ⬜ Real Airflow DAG orchestrating the pipeline end to end (today the pipeline is triggered manually via `databricks bundle run`/CLI scripts, not an Airflow DAG -- only placeholder validation DAGs exist)

## Phase 3 — Data Lake

- ✅ Postgres extraction → `raw/` → Bronze → Silver, validated end to end against real Postgres/S3/Databricks for 7 entities (customers, orders, order_items, products, payments, sellers, categories)
- ✅ Silver registered in the Glue Catalog (`SilverCatalogRegistrationStage`)
- Gold is no longer a Spark/Databricks stage here -- moved to dbt (see ADR-011 and Phase 4)

## Phase 4 — Data Modeling

- ✅ dbt project scaffolded (`dbt/`), real connection to Athena/Glue confirmed (`dbt debug`)
- ✅ Silver sources declared for all 7 entities; `stg_*` staging models implemented and tested against real Athena data for all 7
- ✅ `int_`/`dim_`/`fact_` Gold models: `int_order_items_enriched`, `dim_customers`, `dim_products`, `fact_orders` (star schema, table-materialized, `fact_orders` partitioned by `order_year`/`order_month`) -- `dbt run`/`dbt test` both green against real Athena
- ⬜ Metrics layer

## Phase 5 — Analytics

- ⬜ Dashboards
- ⬜ Business KPIs

## Phase 6 — Observability

- ⬜ Logging
- ⬜ Metrics
- ⬜ Alerts

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