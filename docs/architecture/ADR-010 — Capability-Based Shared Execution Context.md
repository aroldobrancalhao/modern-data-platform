# ADR-010 — Capability-Based Shared Execution Context

- **Status:** Accepted
- **Date:** 2026-07-27
- **Authors:** Modern Data Platform Team

---

# Context

The Modern Data Platform is designed as an enterprise-grade, cloud-agnostic Data Engineering framework capable of orchestrating, executing, monitoring and governing data processing workloads across multiple technologies.

Unlike traditional ETL frameworks that are tightly coupled to specific products, this platform aims to support multiple providers without requiring changes to the execution engine.

Examples include:

- Apache Airflow
- Prefect
- Dagster
- Databricks
- Apache Spark
- Amazon EMR
- Amazon S3
- Azure Data Lake Storage
- Google Cloud Storage
- Apache Kafka
- Amazon MSK
- Amazon Glue
- Unity Catalog
- Hive Metastore
- dbt
- Amazon Athena
- Power BI

Supporting these technologies without introducing architectural coupling requires a common communication mechanism between providers and the execution engine.

This ADR defines that mechanism.

---

# Problem Statement

Execution components exchange information continuously during pipeline execution.

Examples include:

- Workflow identifiers
- Job identifiers
- Dataset metadata
- Storage locations
- Catalog objects
- Runtime metrics
- Exception details
- Retry information
- Monitoring identifiers

Historically these values are often exchanged using string literals.

Example:

```python
context.set("run_id", run_id)

context.set("dataset", dataset)

context.set("bucket", bucket)
```

Although simple, this approach introduces several problems.

## String literals are not discoverable

There is no central definition describing which keys exist.

Developers often create different names for the same concept.

Examples:

```
run_id

workflow_run

workflow_run_id

airflow_run_id
```

All represent the same information.

---

## Lack of validation

Misspelled keys are silently accepted.

```python
context.set("workflwo_run_id", value)
```

This creates runtime errors that are difficult to diagnose.

---

## Vendor coupling

Technology-specific keys naturally emerge.

Examples:

```
airflow_run_id

spark_job_id

s3_bucket

kafka_topic
```

These concepts become embedded inside the execution engine.

As the number of supported technologies grows, the execution engine gradually becomes aware of implementation details that belong exclusively to providers.

This directly violates the architectural principle of provider isolation established by the platform.

---

## Difficult extensibility

Introducing a new orchestration engine frequently requires changes across multiple execution components because no common vocabulary exists.

---

# Decision Drivers

The architecture shall satisfy the following requirements.

## Provider independence

The execution engine MUST never depend on a specific product.

It may only depend on architectural capabilities.

---

## Strong typing

Shared execution keys SHOULD be discoverable through the type system.

---

## Single vocabulary

Every execution concept MUST have a unique canonical identifier.

---

## Extensibility

Adding support for a new provider SHOULD require changes only inside that provider.

---

## Long-term maintainability

The solution MUST remain stable as new cloud vendors, orchestration engines and execution frameworks are introduced.

---

# Decision

The platform adopts a **Capability-Based Shared Execution Context**.

Execution state SHALL be exchanged through a shared ProcessingContext.

Every value stored inside the ProcessingContext MUST be identified using strongly typed ContextKeys.

Each ContextKey represents an architectural capability rather than a technology.

Examples:

| Capability | Example |
|------------|---------|
| Workflow | workflow.run_id |
| Compute | compute.job_id |
| Storage | storage.uri |
| Dataset | dataset.layer |
| Messaging | messaging.topic |
| Catalog | catalog.table |

The execution engine SHALL only understand these capabilities.

It SHALL never understand vendor-specific concepts.

---

# Architectural Principle

The platform distinguishes between products and capabilities.

Products implement capabilities.

The execution engine depends exclusively on capabilities.

```
+-------------------------------+
|        Execution Engine        |
+-------------------------------+
               |
               |
      Platform Contracts
               |
+--------------+--------------+
|              |              |
Workflow     Storage      Compute
Capability   Capability   Capability
|              |              |
|              |              |
Airflow       S3         Databricks
Prefect       GCS        EMR
Dagster       ADLS       Spark Local
```

This separation ensures that introducing a new technology does not require modifications to the execution engine.

Provider implementations are resolved during platform bootstrap.

Execution state is shared exclusively through the ProcessingContext.

---

# Shared Execution Context

The ProcessingContext becomes the canonical state container shared by every execution component.

```

Policy Engine
│
▼
ProcessingContext
▲
│
Workflow Provider
│
Compute Provider
│
Storage Provider
│
Messaging Provider
│
Monitoring Provider

```

Each component contributes information relevant to its capability.

No component is allowed to expose implementation-specific objects to unrelated layers.

---

# Capability Domains

The shared context is divided into capability domains.

```

execution

processing

workflow

compute

storage

dataset

catalog

messaging

cache

monitoring

```

Each domain owns its own strongly typed key definitions.

Example:

```

WorkflowKeys.RUN_ID

StorageKeys.URI

ComputeKeys.JOB_ID

CatalogKeys.TABLE

MessagingKeys.TOPIC

```

This organization guarantees semantic consistency while allowing independent evolution of each capability.

---

# Why Capabilities Instead of Products?

The following comparison illustrates the architectural difference.

| Product-Oriented | Capability-Oriented |
|------------------|---------------------|
| airflow_run_id | workflow.run_id |
| spark_job_id | compute.job_id |
| s3_bucket | storage.bucket |
| kafka_topic | messaging.topic |
| glue_database | catalog.database |

Products become implementation details.

Capabilities become architectural contracts.

This is the fundamental principle established by this ADR.

---

# ProcessingContext

The ProcessingContext is the canonical execution state shared by the entire processing runtime.

It provides a single source of truth during pipeline execution while maintaining strict separation of concerns between execution components.

Unlike a generic dictionary, the ProcessingContext exposes a well-defined contract through strongly typed ContextKeys.

Every component participating in the execution lifecycle may read or write information to the ProcessingContext, provided that the corresponding Platform contract is respected.

---

# Responsibilities

The ProcessingContext is responsible for:

- sharing execution state
- transporting metadata between providers
- exposing execution information to policies
- exposing execution information to hooks
- preserving execution traceability
- enabling provider interoperability

The ProcessingContext is **not** responsible for:

- orchestrating execution
- implementing business rules
- provider-specific logic
- dependency injection
- service discovery

---

# Responsibility Separation

The platform separates service resolution from execution state.

ProviderRegistry is responsible for resolving provider implementations.

ProcessingContext is responsible exclusively for sharing execution state.

SequentialExecutor coordinates execution using both abstractions without coupling them together.

---

# Why ProcessingContext Instead of ExecutionContext?

Several alternatives were evaluated.

## Alternative A — ExecutionContext

```
ExecutionContext

├── workflow
├── storage
├── compute
├── catalog
├── monitoring
├── policies
├── hooks
├── cache
├── ...
```

Advantages

- Single object

Disadvantages

- Excessive responsibilities
- Difficult evolution
- Strong coupling
- Poor separation of concerns

The ExecutionContext naturally grows over time until it becomes the center of the entire framework.

This architecture was rejected.

---

## Alternative B — Independent Contexts

```
WorkflowContext

StorageContext

ComputeContext

MonitoringContext

...
```

Advantages

- High specialization

Disadvantages

- Large amount of object synchronization
- Complex provider communication
- High implementation cost
- Difficult state propagation

This alternative was also rejected.

---

## Adopted Architecture

The platform adopts a shared ProcessingContext accompanied by specialized read models.

```
                   ProcessingContext
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
   PolicyContext      HookContext     Future Contexts
```

The ProcessingContext owns the execution state.

Specialized contexts expose only the information relevant to their consumers.

---

# Context Ownership

Each execution component owns a subset of the shared state.

```
Workflow Provider

        │

        ▼

WorkflowKeys.*

```

```
Compute Provider

        │

        ▼

ComputeKeys.*

```

```
Storage Provider

        │

        ▼

StorageKeys.*

```

```
Messaging Provider

        │

        ▼

MessagingKeys.*

```

No provider may create arbitrary execution keys.

All shared values MUST belong to a defined capability.

---

# ContextKeys

ContextKeys define the canonical vocabulary of the platform.

Instead of exchanging arbitrary strings, execution components communicate using strongly typed enumerations.

Example

Instead of

```python
context.set("run_id", run_id)
```

the platform uses

```python
context.set(
    WorkflowKeys.RUN_ID,
    run_id,
)
```

This approach guarantees consistency throughout the entire platform.

---

# Design Principles

Every ContextKey MUST satisfy the following principles.

## Strong Typing

Every key SHALL be represented by a StrEnum.

Example

```python
@unique
class WorkflowKeys(StrEnum):

    RUN_ID = "workflow.run_id"
```

---

## Uniqueness

Every ContextKey enumeration MUST be decorated with @unique.

Duplicate values are considered programming errors.

---

## Capability-Based Naming

Keys describe architectural concepts.

They never describe technologies.

Correct

```
workflow.run_id

storage.uri

compute.job_id

catalog.table
```

Incorrect

```
airflow_run_id

spark_job_id

s3_bucket

glue_database
```

---

## Stable Contracts

Once introduced, ContextKeys SHOULD remain backward compatible.

Changing an existing key may invalidate providers, policies, hooks and runtime extensions.

---

# Capability Domains

The platform currently defines the following capability domains.

```
ExecutionKeys

ProcessingKeys

WorkflowKeys

ComputeKeys

StorageKeys

DatasetKeys

CatalogKeys

MessagingKeys

CacheKeys

MonitoringKeys
```

Each capability owns its own namespace.

---

# ExecutionKeys

ExecutionKeys describe the lifecycle of the execution itself.

Examples

```
execution.execution_id

execution.parent_execution_id

execution.correlation_id

execution.status

execution.start_time

execution.end_time

execution.duration
```

ExecutionKeys are created by the execution runtime.

---

# ProcessingKeys

ProcessingKeys represent mutable execution state.

Examples

```
processing.current_stage

processing.current_attempt

processing.max_attempts

processing.exception

processing.pipeline_result

processing.stage_result

processing.cancelled

processing.input

processing.output
```

These values evolve continuously during execution.

---

# WorkflowKeys

WorkflowKeys represent orchestration metadata.

Examples

```
workflow.workflow_id

workflow.workflow_name

workflow.run_id

workflow.task_id

workflow.task_name

workflow.execution_url

workflow.schedule_id
```

Workflow providers are responsible for populating these values.

---

# ComputeKeys

ComputeKeys represent processing infrastructure.

Examples

```
compute.job_id

compute.job_name

compute.run_id

compute.session_id

compute.cluster_id

compute.application_id
```

These values are typically generated by distributed compute engines.

---

# StorageKeys

StorageKeys identify persisted data.

Examples

```
storage.uri

storage.path

storage.bucket

storage.object_key

storage.version

storage.etag
```

The runtime never assumes object storage.

Local filesystems, HDFS and cloud storage are equally supported.

---

# DatasetKeys

DatasetKeys describe logical datasets.

Examples

```
dataset.name

dataset.domain

dataset.layer

dataset.version

dataset.partition

dataset.location

dataset.format
```

These concepts remain independent from the underlying storage technology.

---

# CatalogKeys

CatalogKeys describe metadata catalogs.

Examples

```
catalog.catalog

catalog.database

catalog.schema

catalog.table

catalog.view
```

Catalog providers populate these values independently of the chosen metastore.

---

# MessagingKeys

MessagingKeys represent event streaming metadata.

Examples

```
messaging.message_id

messaging.key

messaging.topic

messaging.partition

messaging.offset

messaging.consumer_group
```

---

# CacheKeys

CacheKeys describe distributed cache state.

Examples

```
cache.lock_id

cache.lease_id

cache.ttl
```

---

# MonitoringKeys

MonitoringKeys provide observability metadata.

Examples

```
monitoring.trace_id

monitoring.span_id

monitoring.request_id

monitoring.metric_namespace
```

These identifiers allow execution traces to be correlated across multiple providers.

---

# Public API

The package exports all ContextKey enumerations through a single entry point.

```
processing.core.context_keys
```

This becomes the canonical import location for every execution component.

```
from data_platform.processing.core.context_keys import WorkflowKeys
```

The internal file organization remains hidden from consumers.

---

# Architectural Consequences

This decision establishes a stable execution vocabulary shared by the entire platform.

Providers become responsible for translating product-specific concepts into Platform contracts.

The runtime no longer depends on vendor terminology.

This separation dramatically simplifies future integrations while preserving a consistent execution model.

# Provider Integration Architecture

One of the primary goals of the Modern Data Platform is complete separation between the execution runtime and infrastructure technologies.

The runtime must never depend on products.

It depends exclusively on architectural capabilities.

```
                 Runtime
                    │
                    │
            Platform Contracts
                    │
    ┌───────────────┼────────────────┐
    │               │                │
 Workflow       Compute         Storage
 Provider       Provider        Provider
    │               │                │
    ▼               ▼                ▼
 Airflow      Databricks          S3
 Prefect      EMR                 ADLS
 Dagster      Spark Local         GCS
```

Every provider translates vendor-specific concepts into platform capabilities.

The runtime never communicates directly with infrastructure products.

---

# Runtime Bootstrap

The execution environment is assembled during platform bootstrap.

The bootstrap process is responsible for:

- creating the ProviderRegistry
- registering provider implementations
- creating the ProcessingContext
- creating the execution runtime

After initialization, the execution engine consumes only:

- ProviderRegistry
- ProcessingContext

No execution component is responsible for service discovery or provider initialization.

---

# Workflow Providers

Workflow providers are responsible for pipeline orchestration.

Examples

- Apache Airflow
- Prefect
- Dagster
- AWS Step Functions
- Azure Data Factory

All workflow providers expose the same conceptual operations.

```
trigger()

cancel()

pause()

resume()

get_status()

get_run()

get_logs()
```

Although implementation differs, every provider writes identical information into the ProcessingContext.

```
WorkflowKeys.WORKFLOW_ID

WorkflowKeys.WORKFLOW_NAME

WorkflowKeys.RUN_ID

WorkflowKeys.TASK_ID

WorkflowKeys.TASK_NAME

WorkflowKeys.EXECUTION_URL

WorkflowKeys.SCHEDULE_ID
```

The execution engine never knows whether the orchestration engine is Airflow or Prefect.

---

# Apache Airflow

Airflow becomes simply one implementation of WorkflowProvider.

```
                 WorkflowProvider
                        ▲
                        │
                AirflowProvider
                        │
                        ▼
                 Airflow REST API
```

Responsibilities

- trigger DAGs
- retrieve DAG runs
- monitor execution
- cancel executions
- collect metadata

Provider-specific concepts

```
dag_id

dag_run_id

task_instance

logical_date
```

are translated into

```
WorkflowKeys.*
```

before reaching the execution engine.

No Airflow terminology propagates beyond the provider boundary.

---

# Prefect

Prefect follows exactly the same contract.

```
Flow Run

Deployment

Task Run
```

becomes

```
WorkflowKeys.RUN_ID

WorkflowKeys.TASK_ID
```

No runtime changes are required.

---

# Dagster

Dagster introduces different terminology.

```
Job

Run

Asset

Op
```

These concepts are translated into

```
WorkflowKeys.*

DatasetKeys.*
```

Again, the runtime remains unchanged.

---

# Compute Providers

Compute providers execute processing workloads.

Examples

- Databricks
- Apache Spark
- Amazon EMR
- Kubernetes Spark Operator
- Local Spark

```
            ComputeProvider
                    ▲
     ┌──────────────┼──────────────┐
     │              │              │
 Databricks       EMR         Spark Local
```

Every provider publishes

```
ComputeKeys.JOB_ID

ComputeKeys.RUN_ID

ComputeKeys.APPLICATION_ID

ComputeKeys.SESSION_ID

ComputeKeys.CLUSTER_ID
```

The runtime never depends on Spark implementation details.

---

# Databricks

Databricks becomes a ComputeProvider implementation.

Responsibilities

- submit jobs
- monitor execution
- retrieve job status
- retrieve cluster information
- collect execution metadata

Provider terminology

```
Job ID

Run ID

Cluster ID

Workspace
```

is translated into

```
ComputeKeys.*
```

before entering the shared context.

---

# Amazon EMR

Amazon EMR exposes different APIs.

Internally it uses

```
Cluster

Step

Application
```

These become

```
ComputeKeys.CLUSTER_ID

ComputeKeys.RUN_ID

ComputeKeys.APPLICATION_ID
```

The execution runtime sees exactly the same information.

---

# Storage Providers

Storage providers persist data.

Examples

- Amazon S3
- Azure Data Lake Storage
- Google Cloud Storage
- HDFS
- Local Filesystem
- MinIO

```
             StorageProvider
                    ▲
      ┌─────────────┼──────────────┐
      │             │              │
      S3           ADLS           GCS
```

Every provider publishes

```
StorageKeys.URI

StorageKeys.PATH

StorageKeys.BUCKET

StorageKeys.OBJECT_KEY

StorageKeys.VERSION
```

The runtime never assumes object storage.

---

# Amazon S3

S3 internally works with

```
Bucket

Object

Version

ETag
```

These concepts are translated into

```
StorageKeys.*
```

before reaching execution components.

---

# Azure Data Lake

ADLS has different terminology.

Internally

```
Filesystem

Directory

Path
```

becomes

```
StorageKeys.URI

StorageKeys.PATH
```

The execution engine remains storage-independent.

---

# Messaging Providers

Messaging providers support event-driven processing.

Examples

- Apache Kafka
- Amazon MSK
- Redpanda
- Google Pub/Sub
- Azure Event Hub

Every implementation publishes

```
MessagingKeys.MESSAGE_ID

MessagingKeys.KEY

MessagingKeys.TOPIC

MessagingKeys.PARTITION

MessagingKeys.OFFSET
```

The runtime does not know whether events originate from Kafka or Pub/Sub.

---

# Kafka

Kafka terminology

```
Topic

Partition

Offset

Key
```

maps directly to

```
MessagingKeys.*
```

Debezium simply becomes another producer using the same vocabulary.

No CDC-specific behavior is required inside the execution engine.

---

# Metadata Catalog Providers

Catalog providers manage metadata.

Examples

- AWS Glue Catalog
- Unity Catalog
- Hive Metastore

```
             CatalogProvider
                    ▲
      ┌─────────────┼──────────────┐
      │             │              │
     Glue      Unity Catalog      Hive
```

Every provider publishes

```
CatalogKeys.CATALOG

CatalogKeys.DATABASE

CatalogKeys.SCHEMA

CatalogKeys.TABLE

CatalogKeys.VIEW
```

The runtime never depends on catalog technology.

---

# AWS Glue

Glue maintains

```
Database

Table

Partition
```

The provider converts these concepts into

```
CatalogKeys.*
```

before exposing them to the runtime.

---

# Unity Catalog

Unity Catalog introduces additional governance concepts.

Those remain internal to the provider.

Only Platform contracts become visible to the execution engine.

---

# Transformation Providers

Data transformations represent another capability.

The platform introduces a TransformationProvider abstraction.

Examples

- dbt
- Spark SQL
- DuckDB
- Polars
- Pandas

```
         TransformationProvider
                    ▲
      ┌─────────────┼──────────────┐
      │             │              │
     dbt        Spark SQL       DuckDB
```

Transformations are responsible for producing datasets.

Typical ContextKeys include

```
DatasetKeys.DATASET

DatasetKeys.LAYER

DatasetKeys.VERSION

CatalogKeys.TABLE
```

---

# dbt Integration

dbt is modeled as a TransformationProvider.

Responsibilities

- execute models
- execute snapshots
- execute tests
- execute seeds
- publish metadata

The execution engine does not understand dbt.

It only understands datasets.

dbt-specific concepts remain isolated inside the provider.

---

# Query Providers

Query engines consume datasets.

Examples

- Amazon Athena
- Trino
- Presto
- DuckDB

They typically consume

```
StorageKeys.URI

CatalogKeys.TABLE

DatasetKeys.LAYER
```

No provider-specific logic exists inside the runtime.

---

# Observability

Observability providers consume MonitoringKeys.

Examples

- CloudWatch
- OpenTelemetry
- Grafana
- Prometheus

Every execution receives

```
MonitoringKeys.TRACE_ID

MonitoringKeys.SPAN_ID

MonitoringKeys.REQUEST_ID
```

allowing distributed tracing across the entire platform.

---

# Capability Independence

The following diagram summarizes the architectural model.

```
                    ProcessingContext
                           │
 ┌─────────────┬────────────┼─────────────┬─────────────┐
 │             │            │             │             │
 ▼             ▼            ▼             ▼             ▼
Workflow    Compute     Storage      Catalog     Messaging
Provider    Provider    Provider     Provider    Provider
 │             │            │             │             │
 ▼             ▼            ▼             ▼             ▼
Airflow   Databricks      S3         Glue        Kafka
Prefect      EMR         ADLS       Unity      Redpanda
Dagster   Spark Local     GCS        Hive       Pub/Sub
```

Every provider speaks the language of its own technology.

Every provider translates that language into Platform contracts.

The execution engine understands only those contracts.

This separation ensures that infrastructure can evolve independently of the runtime.

# Future Evolution

The Capability-Based Shared Execution Context establishes a stable architectural foundation for the long-term evolution of the Modern Data Platform.

Future integrations shall extend the platform by implementing new providers rather than modifying the execution runtime.

This dramatically reduces architectural risk while allowing continuous expansion of supported technologies.

---

# Reference Architecture

The following diagram summarizes the complete execution architecture.

```text
                                   Modern Data Platform

                                            │
                                            │
                                   Pipeline Definition
                                            │
                                            ▼
                                 SequentialExecutor
                                            │
                                            ▼
                                    Policy Engine
                                            │
                                            ▼
                                  ProcessingContext
                                            │
      ┌─────────────────────────────────────┼─────────────────────────────────────┐
      │                                     │                                     │
      ▼                                     ▼                                     ▼
 Workflow Provider                   Compute Provider                     Storage Provider
      │                                     │                                     │
      ▼                                     ▼                                     ▼
 Airflow / Prefect                 Databricks / EMR                    S3 / ADLS / GCS
 Dagster                           Spark Local                         HDFS / Local FS

      ┌─────────────────────────────────────┼─────────────────────────────────────┐
      ▼                                     ▼                                     ▼
 Messaging Provider                Catalog Provider               Transformation Provider
      │                                     │                                     │
      ▼                                     ▼                                     ▼
 Kafka / MSK                    Glue / Unity Catalog                   dbt
 Redpanda                       Hive Metastore                         Spark SQL
 Pub/Sub                                                           DuckDB / Polars

                                            │
                                            ▼
                                  Query / BI Consumers
                                            │
                      ┌─────────────────────┼─────────────────────┐
                      ▼                     ▼                     ▼
                   Athena                Trino               Power BI
```

The execution runtime never communicates directly with any infrastructure product.

Every interaction occurs through Platform contracts.

---

# Provider Responsibilities

Every provider follows the same lifecycle.

```text
External Technology

        │

        ▼

Provider

        │

Translate vendor concepts

        │

        ▼

ContextKeys

        │

        ▼

ProcessingContext

        │

        ▼

Execution Runtime
```

Providers own translation.

The runtime owns execution.

This separation represents one of the primary architectural principles of the platform.

---

# Benefits

## Technology Independence

Infrastructure vendors can be replaced without changing the runtime.

Examples

Airflow

↓

Prefect

No runtime modifications.

---

Databricks

↓

EMR

No runtime modifications.

---

Glue

↓

Unity Catalog

No runtime modifications.

---

S3

↓

Azure Data Lake

No runtime modifications.

---

Kafka

↓

Amazon MSK

↓

Redpanda

No runtime modifications.

---

## Better Testability

Providers become independently testable.

Execution tests no longer require infrastructure.

Provider tests no longer require execution internals.

---

## Better Maintainability

Capabilities evolve independently.

Workflow improvements do not impact Storage.

Storage improvements do not impact Compute.

Monitoring improvements do not impact Catalog.

---

## Better Discoverability

Every shared execution concept has exactly one canonical definition.

Developers no longer need to search for arbitrary string literals.

---

## Better IDE Support

Using StrEnum enables

- autocomplete
- static analysis
- rename refactoring
- navigation
- duplicate detection

---

## Better Governance

The platform gains a stable execution vocabulary.

This vocabulary becomes part of the public architecture.

Every new provider must conform to this vocabulary.

---

# Trade-offs

This architecture introduces additional abstraction.

Providers must translate infrastructure concepts into Platform contracts.

This requires slightly more implementation effort.

However, the long-term reduction in coupling largely outweighs this cost.

The decision favors maintainability over implementation convenience.

---

# Consequences

## Positive

Strong typing

Technology independence

Provider isolation

Better testing

Simpler maintenance

Cleaner architecture

Long-term extensibility

Cloud agnostic design

Enterprise-ready architecture

---

## Negative

More abstraction

Additional provider implementations

Slightly larger codebase

Translation layer required

---

The architectural benefits justify these costs.

---

# Compatibility

This architecture has been designed to support future integrations including but not limited to

Workflow

- Apache Airflow
- Prefect
- Dagster
- AWS Step Functions

Compute

- Databricks
- Apache Spark
- Amazon EMR
- Kubernetes Spark Operator

Storage

- Amazon S3
- Azure Data Lake Storage
- Google Cloud Storage
- HDFS
- Local Filesystem
- MinIO

Messaging

- Apache Kafka
- Amazon MSK
- Redpanda
- Google Pub/Sub
- Azure Event Hub

Catalog

- AWS Glue
- Unity Catalog
- Hive Metastore

Transformation

- dbt
- Spark SQL
- DuckDB
- Polars
- Pandas

Query

- Athena
- Trino
- Presto
- DuckDB

Monitoring

- OpenTelemetry
- CloudWatch
- Prometheus
- Grafana

Visualization

- Power BI
- Apache Superset
- Tableau

---

# Implementation Guidelines

Future contributors SHALL follow these rules.

Every new shared execution value MUST belong to an existing capability whenever possible.

Technology names MUST NOT appear inside the execution runtime.

Every shared execution key MUST be implemented as a StrEnum decorated with @unique.

Every key MUST use a namespaced value.

Example

workflow.run_id

storage.uri

catalog.table

Never

airflow_run_id

spark_job

s3_bucket

glue_database

Providers SHALL translate infrastructure terminology.

The runtime SHALL consume only capability terminology.

---

# Roadmap

The following architectural milestones build directly upon this ADR.

## Phase 1

Introduce ContextKeys

Replace string literals

Strengthen ProcessingContext

Status

Completed

---

## Phase 2

Policy Engine integration

Execution policies

Retry policies

Cancellation policies

Timeout policies

Circuit breaker

---

## Phase 3

Hook Engine evolution

Lifecycle hooks

Audit hooks

Metrics hooks

Tracing hooks

Notifications

---

## Phase 4

Workflow Providers

Airflow

Prefect

Dagster

---

## Phase 5

Compute Providers

Databricks

Spark Local

Amazon EMR

---

## Phase 6

Storage Providers

Amazon S3

Azure Data Lake

Google Cloud Storage

---

## Phase 7

Messaging Providers

Kafka

Redpanda

Amazon MSK

Debezium integration

---

## Phase 8

Catalog Providers

Glue

Unity Catalog

Hive

---

## Phase 9

Transformation Providers

dbt

Spark SQL

DuckDB

Polars

---

## Phase 10

Query Providers

Athena

Trino

Presto

---

## Phase 11

Observability

OpenTelemetry

CloudWatch

Grafana

Prometheus

---

# Final Decision

The Modern Data Platform adopts a Capability-Based Shared Execution Context.

Execution components communicate exclusively through strongly typed Platform contracts.

Infrastructure technologies remain isolated behind provider implementations.

This decision establishes a stable architectural foundation capable of supporting the long-term evolution of the platform while preserving provider independence, cloud agnosticism and architectural consistency.

This ADR is considered a permanent architectural decision and SHALL guide all future provider implementations.