# ADR-004: Repository Structure

- **Status:** Accepted
- **Date:** 2026-07-19
- **Decision Makers:** Project Maintainers

---

# Context

As data platforms evolve, repositories often become difficult to maintain due to inconsistent organization, duplicated responsibilities, and tightly coupled components.

A well-defined repository structure improves maintainability, discoverability, onboarding, scalability, and long-term evolution.

This document defines the official repository organization for the Modern Data Platform.

---

# Decision

The repository shall be organized by platform capabilities rather than technologies.

Each directory represents a business or platform responsibility.

Cloud-specific implementations remain isolated from business logic.

---

# Repository Overview

```
modern-data-platform/

├── .github/
│
├── docs/
│
├── infrastructure/
│
├── src/
│
├── tests/
│
├── scripts/
│
├── docker/
│
├── notebooks/
│
├── dbt/
│
├── simulator/
│
├── .env.example
├── pyproject.toml
├── poetry.lock
├── README.md
├── LICENSE
├── CONTRIBUTING.md
└── CHANGELOG.md
```

---

# Source Code Organization

```
src/

    platform/

    cloud/

    ingestion/

    streaming/

    processing/

    quality/

    orchestration/

    analytics/

    common/
```

Each directory has a single responsibility.

---

# platform/

The Platform Layer contains infrastructure-independent abstractions.

```
platform/

    config/

    storage/

    compute/

    messaging/

    catalog/

    monitoring/

    security/

    identity/

    notifications/
```

Responsibilities

- Contracts
- Interfaces
- Base implementations
- Shared services

This package must never depend on cloud providers.

---

# cloud/

Contains provider implementations.

```
cloud/

    aws/

    azure/

    gcp/

    local/
```

Each provider implements Platform contracts.

Example

```
cloud/

    aws/

        storage/

        compute/

        catalog/

        messaging/

        monitoring/

    azure/

    gcp/

    local/
```

Cloud SDKs belong only inside this directory.

---

# ingestion/

Responsible for data ingestion.

Examples

- Database connectors
- File ingestion
- API ingestion
- CDC consumers

Responsibilities

- Receive data
- Validate payloads
- Publish events

Not responsible for business transformations.

---

# streaming/

Responsible for event streaming.

Examples

- Kafka consumers
- Kafka producers
- Event serialization
- Topics

Streaming components should remain lightweight.

---

# processing/

Responsible for data processing.

Examples

- Spark jobs
- Databricks notebooks
- Bronze processing
- Silver processing
- Gold processing

Typical structure

```
processing/

    bronze/

    silver/

    gold/

    shared/
```

Business transformations belong here.

---

# quality/

Responsible for data quality.

Examples

- Validation rules
- Expectations
- Data profiling
- Schema validation

Possible tools

- Great Expectations
- Deequ
- Custom validators

---

# orchestration/

Responsible for workflow orchestration.

Current implementation

- Apache Airflow

Structure

```
orchestration/

    dags/

    operators/

    sensors/

    tasks/

    schedules/
```

Orchestration should not implement business logic.

---

# analytics/

Responsible for analytical artifacts.

Examples

- Athena views
- Semantic models
- BI assets
- Data marts

Future additions may include:

- Metrics layer
- Feature Store
- ML datasets

---

# common/

Shared utilities.

Examples

- Exceptions
- Constants
- Helpers
- Logging
- Utilities

Business logic should remain outside this package whenever possible.

---

# infrastructure/

Infrastructure as Code.

```
infrastructure/

    terraform/

        modules/

        providers/

            aws/

            azure/

            gcp/

    environments/

        local/

        dev/

        staging/

        production/
```

Infrastructure must remain isolated from application code.

---

# tests/

```
tests/

    unit/

    integration/

    contract/

    e2e/

    performance/
```

Every module should have corresponding tests.

---

# notebooks/

Exploratory notebooks.

Structure

```
notebooks/

    exploration/

    experiments/

    prototypes/
```

Production logic must never live inside notebooks.

---

# dbt/

```
dbt/

    models/

        bronze/

        silver/

        gold/

    snapshots/

    seeds/

    tests/

    macros/
```

dbt is responsible for analytical modeling.

---

# simulator/

Responsible for synthetic data generation.

Examples

- Customers
- Orders
- Products
- Payments
- Inventory

The simulator should be completely independent from the platform.

---

# docker/

Contains local development resources.

```
docker/

    airflow/

    kafka/

    postgres/

    spark/

    minio/

    debezium/
```

Each service owns its own configuration.

---

# scripts/

Automation scripts.

Examples

- Environment setup
- Local bootstrap
- Data generation
- Maintenance

Scripts should remain idempotent whenever possible.

---

# Documentation Organization

```
docs/

    architecture/

    diagrams/

    api/

    guides/

    tutorials/

    roadmap/

    decisions/
```

Architecture documentation remains version-controlled.

---

# Naming Conventions

Packages

```
snake_case
```

Examples

```
processing

storage_provider

catalog
```

Classes

```
PascalCase
```

Examples

```
StorageProvider

SparkJob

KafkaProducer
```

Functions

```
snake_case
```

Examples

```
load_data()

publish_event()

run_pipeline()
```

Constants

```
UPPER_SNAKE_CASE
```

---

# Dependency Rules

Allowed

```
Business

↓

Platform

↓

Contracts

↓

Providers

↓

Infrastructure
```

Forbidden

```
Business

↓

Cloud SDK
```

Also forbidden

```
Airflow DAG

↓

boto3
```

or

```
Spark Job

↓

Azure SDK
```

Every infrastructure dependency must pass through Platform contracts.

---

# Evolution Guidelines

Adding a new feature should not require restructuring the repository.

Typical examples

New storage provider

```
cloud/oracle/storage/
```

New orchestration engine

```
orchestration/prefect/
```

New messaging implementation

```
cloud/aws/msk/
```

The repository organization remains stable.

---

# Trade-offs

Advantages

- Excellent discoverability
- Clear ownership
- Better scalability
- Easier onboarding
- Modular architecture
- Easier testing

Disadvantages

- Slightly larger directory tree
- More initial organization effort

These trade-offs are intentional.

---

# Consequences

The repository structure becomes part of the platform architecture.

Future implementations should follow this organization unless a new ADR explicitly changes it.

---

# Related ADRs

- ADR-000 – Architecture Principles
- ADR-001 – Platform Architecture
- ADR-002 – Platform Contracts
- ADR-003 – Cloud Strategy
- ADR-005 – Development Standards