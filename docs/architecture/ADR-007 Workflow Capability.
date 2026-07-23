# ADR-007: Workflow Capability

- Status: Accepted
- Date: 2026-07-23
- Deciders: Project Maintainers

---

# Context

The platform currently exposes independent capabilities for interacting with infrastructure and processing engines.

Current capabilities:

- Storage
- Catalog
- Compute

Each capability is defined by an abstraction inside `data_platform` and implemented by one or more providers under `integrations`.

Examples:

```
StorageProvider
    ├── AWS S3

CatalogProvider
    ├── AWS Glue

ComputeProvider
    └── Databricks
```

Although data processing is already abstracted through the `ComputeProvider`, the platform does not currently expose an abstraction responsible for workflow orchestration.

Workflow orchestration is a different concern from distributed data processing.

The Compute capability executes workloads.

The Workflow capability schedules, triggers, monitors and controls workflows.

Because orchestration engines may vary (Apache Airflow, MWAA, Astronomer, Dagster, Prefect, etc.), orchestration must be treated as another platform capability rather than being tightly coupled to a specific product.

---

# Decision

Introduce a new platform capability named **Workflow**.

The Workflow capability will become part of the public Platform API alongside Storage, Catalog and Compute.

```
Platform

    storage()

    catalog()

    compute()

    workflow()
```

Workflow orchestration will be defined through a provider contract.

Concrete orchestration engines will implement this contract.

The first implementation will be Apache Airflow.

---

# Responsibilities

The Workflow capability is responsible for:

- Triggering workflows
- Monitoring workflow execution
- Querying workflow status
- Cancelling workflow executions
- Listing workflow runs
- Accessing execution metadata

The capability is intentionally orchestration-oriented.

It is **not responsible** for:

- Data processing
- Spark execution
- Storage operations
- Metadata catalog operations
- Business transformations
- DAG implementation logic

---

# Architecture

```
                    Platform
                        │
     ┌──────────────────┼──────────────────┐
     │                  │                  │
 StorageProvider   CatalogProvider   ComputeProvider
                                              │
                                       WorkflowProvider
```

Concrete implementations remain outside the platform.

```
integrations/

    aws/

    databricks/

    airflow/
```

The Platform depends only on provider contracts.

Providers never depend on each other.

---

# Provider Contract

The Workflow capability introduces a new provider contract.

```
WorkflowProvider
```

Every orchestration engine must implement this interface.

The Platform never communicates directly with Airflow or any orchestration engine.

Instead it communicates only through the WorkflowProvider abstraction.

---

# Domain Model

The capability introduces three core models.

## Workflow

Represents a workflow definition.

Examples:

- Bronze ingestion
- Silver transformation
- Gold publication

A Workflow is independent from any orchestration engine.

---

## WorkflowRun

Represents one execution of a Workflow.

Contains execution metadata such as:

- identifier
- start time
- end time
- execution parameters
- current status

---

## WorkflowStatus

Represents the lifecycle of a workflow execution.

Typical states include:

- Pending
- Running
- Success
- Failed
- Cancelled

The platform owns the status model.

Provider-specific states must be mapped into these platform states.

---

# Provider Implementation Pattern

Concrete providers should follow the same architectural pattern already adopted by the Databricks Compute provider.

Recommended structure:

```
integrations/

    airflow/

        bootstrap.py

        config/

        core/

        workflow/

            builder.py

            client.py

            mapper.py

            airflow_workflow_provider.py
```

Responsibilities are separated as follows.

## Context

Owns shared resources.

Examples:

- API configuration
- authentication
- HTTP session

---

## Client

Responsible for communicating with the orchestration engine.

No business logic.

No platform abstractions.

---

## Mapper

Maps provider-specific models into platform models.

Example:

```
Airflow DAG Run

        ↓

WorkflowRun
```

---

## Provider

Implements WorkflowProvider.

Coordinates Client and Mapper.

Contains platform behaviour.

---

## Builder

Builds the provider dependency graph.

Creates:

- Context
- Client
- Provider

---

## Bootstrap

Registers the provider into the Platform.

---

# Public API

The Platform should expose a fluent API.

Example:

```python
platform.workflow().trigger(workflow)

platform.workflow().status(run_id)

platform.workflow().cancel(run_id)

platform.workflow().list_runs(workflow)
```

The application never communicates directly with Airflow.

---

# Future Providers

The Workflow capability is orchestration-engine agnostic.

Future implementations may include:

- Apache Airflow
- Amazon MWAA
- Astronomer
- Prefect
- Dagster

No changes to the Platform API should be required when introducing a new provider.

---

# Consequences

## Positive

- Separation of orchestration from processing.
- Cloud-agnostic architecture.
- Consistent provider model across the platform.
- Extensible orchestration layer.
- Stable public Platform API.
- Easier testing through provider abstraction.

## Negative

- Additional abstraction layer.
- Provider implementations require mapping between engine-specific and platform models.

---

# Implementation Order

1. Workflow capability
2. Workflow models
3. Workflow provider contract
4. Platform integration
5. Airflow provider
6. Unit tests
7. Workflow implementations (DAGs)