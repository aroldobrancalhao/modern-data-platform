# ADR-0008- Batch and Streaming Processing Architecture

- Status: Accepted
- Date: 2026-07-24

---

# Context

The Modern Data Platform must demonstrate enterprise-grade Data Engineering
practices while remaining understandable and maintainable.

The platform will support both:

- Batch processing
- Streaming processing

During the architecture discussions several alternatives were evaluated:

- Airflow orchestrating everything
- Kafka orchestrating everything
- Event-driven pipeline for both batch and streaming
- Independent orchestration models

The main goal is to maximize architectural quality while also demonstrating
practical knowledge of modern Data Engineering tools used in the market.

---

# Decision

The platform will adopt two execution modes.

## Batch Processing

Apache Airflow will be the orchestration engine.

Responsibilities:

- Scheduling
- Workflow orchestration
- Retries
- Dependencies
- Sensors
- Task Groups
- Dynamic Tasks
- SLA
- Backfill
- Catchup
- Monitoring

Airflow is responsible only for orchestration.

Business logic remains outside Airflow.

---

## Streaming Processing

Apache Kafka will be responsible for event streaming.

Responsibilities:

- CDC event transport
- Event-driven processing
- Consumer Groups
- Replay
- Offset management
- Retry Topics
- Dead Letter Queue (DLQ)

Kafka is not used as an orchestration engine for batch workloads.

---

# Business Services

The platform exposes reusable services.

```
BronzeService
SilverService
GoldService
```

These services are completely independent from the execution engine.

They do not know whether they were called by:

- Airflow
- Kafka
- API
- CLI
- Tests

This separation keeps business logic isolated from orchestration concerns.

---

# Batch Flow

```
Airflow
    │
    ▼
Extract
    │
    ▼
Raw Validation
    │
    ▼
BronzeService
    │
    ▼
Bronze Data Quality
    │
    ▼
SilverService
    │
    ▼
Silver Data Quality
    │
    ▼
GoldService (dbt)
    │
    ▼
Star Schema (dbt models)
    │
    ▼
Glue Catalog
    │
    ▼
Athena
    │
    ▼
Power BI
```

Airflow controls:

- execution order
- retries
- failures
- dependencies
- scheduling

---

# Streaming Flow

```
PostgreSQL

↓

Debezium CDC

↓

Kafka

↓

Bronze Consumer

↓

BronzeService

↓

SilverService

↓

GoldService
```

Streaming processing is independent from Airflow.

---

# Retry Strategy

Batch:

Retry is managed by Airflow.

Airflow controls:

- retry attempts
- retry delay
- timeout
- failure state
- notifications

Streaming:

Retry is managed by Kafka consumers.

Possible strategies:

- Manual offset commit
- Retry Topics
- Dead Letter Queue
- Idempotent processing

---

# Why Airflow is not waiting for Kafka events

One alternative considered was:

```
Airflow

↓

Bronze

↓

Kafka Event

↓

Silver
```

This approach was rejected.

Reason:

Airflow already provides workflow orchestration,
dependency management and retries.

Using Kafka to coordinate Airflow tasks would duplicate responsibilities.

---

# Why Kafka is not orchestrating Batch

Kafka is an event streaming platform.

Although it can coordinate distributed processing,
using Kafka as the orchestration engine for scheduled batch workflows would
replace several native Airflow features:

- DAG visualization
- Sensors
- Task Groups
- Dynamic Tasks
- SLA
- Retry
- Backfill
- Catchup

Therefore Airflow remains the orchestration engine for batch workloads.

---

# CDC Strategy

Streaming ingestion uses:

```
PostgreSQL

↓

Debezium

↓

Kafka
```

Every database change generates an event.

Consumers invoke the same business services used by Batch.

---

# Event-Driven Processing

The project still demonstrates Event-Driven Architecture.

However, Event-Driven Processing is restricted to Streaming.

Batch remains DAG-oriented.

This separation reflects common enterprise architectures.

---

# Consequences

Advantages

- Clear separation of responsibilities
- High cohesion
- Low coupling
- Reusable business services
- Independent execution modes
- Demonstrates both Batch and Streaming
- Demonstrates Airflow best practices
- Demonstrates Kafka best practices

Disadvantages

- Two orchestration models must be maintained.
- Streaming and Batch have different operational characteristics.

These trade-offs were considered acceptable.