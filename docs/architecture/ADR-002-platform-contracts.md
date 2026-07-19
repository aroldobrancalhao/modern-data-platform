# ADR-002: Platform Contracts

- **Status:** Accepted
- **Date:** 2026-07-19
- **Decision Makers:** Project Maintainers

---

# Context

The Modern Data Platform is designed to support multiple cloud providers, compute engines, messaging systems, and storage technologies without requiring changes to business logic.

To achieve this level of flexibility, infrastructure services must not be consumed directly by the application.

Instead, every external dependency is represented by a platform contract (interface), while provider-specific implementations remain isolated behind these contracts.

This document defines the contracts that compose the Platform Layer.

---

# Decision

The Platform Layer shall expose a set of provider-agnostic contracts.

Business logic, orchestration workflows, notebooks, and processing pipelines must depend only on these contracts.

Concrete implementations are considered infrastructure details.

---

# Design Goals

Platform contracts must:

- Hide infrastructure complexity
- Support multiple providers
- Encourage dependency injection
- Enable unit testing
- Avoid cloud-specific APIs
- Simplify future extensions

---

# Platform Overview

```
                Business Logic

                      │

                      ▼

             Platform Contracts

      ┌─────────┬─────────┬─────────┐

      │         │         │         │

 Storage   Compute   Messaging  Catalog

      │         │         │         │

      ▼         ▼         ▼         ▼

 AWS     Azure     GCP    Local
```

The application communicates only with contracts.

Provider implementations remain interchangeable.

---

# Storage Contract

## Responsibility

Manage object storage operations.

Examples include:

- Upload files
- Download files
- Delete files
- List objects
- Check existence

Business code should never know where data is physically stored.

---

## Expected Operations

Examples:

```
write()

read()

delete()

exists()

list()

copy()

move()
```

Possible implementations:

- Amazon S3
- Azure Data Lake Storage
- Google Cloud Storage
- Local Storage

---

# Compute Contract

## Responsibility

Execute distributed workloads.

The contract hides the execution engine.

---

## Expected Operations

```
submit_job()

run_notebook()

cancel_job()

job_status()

cluster_status()
```

Possible implementations:

- Databricks
- Amazon EMR
- Azure Synapse
- Google Dataproc

---

# Messaging Contract

## Responsibility

Exchange asynchronous events.

Messaging should remain independent from the selected provider.

---

## Expected Operations

```
publish()

subscribe()

ack()

retry()

dead_letter()
```

Possible implementations:

- Apache Kafka
- Azure Event Hubs
- Google Pub/Sub

---

# Catalog Contract

## Responsibility

Expose metadata services.

Examples:

- Tables
- Schemas
- Partitions
- Metadata

---

## Expected Operations

```
create_table()

drop_table()

table_exists()

list_tables()

refresh_metadata()
```

Possible implementations:

- Unity Catalog
- AWS Glue
- Hive Metastore

---

# Configuration Contract

## Responsibility

Provide application configuration.

Configuration sources should remain transparent.

---

## Expected Operations

```
get()

reload()

validate()
```

Possible sources:

- Environment Variables
- YAML
- JSON
- Secret Managers

---

# Secrets Contract

## Responsibility

Retrieve sensitive information.

Business code must never know where secrets are stored.

---

## Expected Operations

```
get_secret()

secret_exists()

refresh_secret()
```

Possible implementations:

- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager

---

# Monitoring Contract

## Responsibility

Publish platform telemetry.

---

## Expected Operations

```
log()

metric()

trace()

event()

health()
```

Possible implementations:

- CloudWatch
- Azure Monitor
- Google Cloud Monitoring
- OpenTelemetry

---

# Identity Contract

## Responsibility

Authenticate platform components.

Possible implementations:

- IAM
- Managed Identity
- Workload Identity

Business logic should never manipulate cloud credentials directly.

---

# Notification Contract

## Responsibility

Notify external systems about platform events.

Examples:

- Pipeline failures
- Successful executions
- SLA violations

Possible implementations:

- Email
- Slack
- Microsoft Teams
- SNS
- Pub/Sub

---

# Dependency Injection

All contracts must be injected.

Example:

```
Processing Service

↓

Storage Provider

↓

S3 Implementation
```

Business code never instantiates providers directly.

---

# Dependency Rule

Allowed:

```
Business

↓

Contract

↓

Provider
```

Forbidden:

```
Business

↓

AWS SDK
```

The same rule applies to every infrastructure dependency.

---

# Versioning

Contracts should evolve conservatively.

Breaking changes require:

- New interface version
- Migration strategy
- Updated implementations

---

# Testing

Every contract must support mocking.

Business logic should be testable without requiring:

- AWS
- Azure
- GCP
- Databricks
- Kafka

---

# Extensibility

Adding a new cloud provider should require only a new implementation.

Example:

```
StorageProvider

    AmazonS3Provider

    AzureStorageProvider

    GoogleCloudStorageProvider

    MinIOStorageProvider
```

No business code should change.

---

# Trade-offs

Advantages

- Excellent testability
- Cloud portability
- Clear architecture
- Loose coupling
- Easier maintenance
- Simpler future migrations

Disadvantages

- Additional interfaces
- Slight increase in abstraction
- More initial implementation effort

These trade-offs are considered acceptable.

---

# Consequences

Every infrastructure component introduced into the platform must first expose a contract.

Provider implementations are considered adapters.

Business logic must remain completely unaware of infrastructure details.

---

# Related ADRs

- ADR-000 – Architecture Principles
- ADR-001 – Platform Architecture
- ADR-003 – Cloud Strategy
- ADR-004 – Repository Structure
- ADR-005 – Development Standards