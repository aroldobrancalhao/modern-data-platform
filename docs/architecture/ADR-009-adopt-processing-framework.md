# ADR-009: Adopt an Internal Processing Framework

- **Status:** Accepted
- **Date:** 2026-07-25
- **Decision Makers:** Modern Data Platform Maintainers

---

# Context

The Modern Data Platform is intended to simulate the architecture of an enterprise-grade Data Engineering platform rather than a collection of isolated ETL pipelines.

Most portfolio projects demonstrate how to use technologies such as Apache Airflow, Apache Spark, Kafka, dbt and cloud services. While technically valuable, they often place business logic directly inside orchestration workflows, tightly coupling data processing with the orchestration engine.

This approach is appropriate for small projects but becomes increasingly difficult to evolve as the number of pipelines, execution strategies and processing requirements grows.

Large organizations commonly separate orchestration concerns from processing concerns by introducing an internal processing framework responsible for executing business pipelines independently of the orchestration platform.

The objective of this project is to follow the same architectural direction.

---

# Problem Statement

Without a dedicated processing layer, orchestration and business execution become tightly coupled.

Typical orchestration-first architectures present several limitations:

- Business logic becomes dependent on a specific orchestrator.
- Pipelines are difficult to execute outside scheduled workflows.
- Retry strategies operate only at task level.
- Parallel execution is delegated entirely to external systems.
- Processing concerns become distributed across multiple DAGs.
- Testing individual processing flows becomes unnecessarily complex.
- Reusing processing logic across projects becomes difficult.

As the platform evolves, every new execution strategy increases the complexity of the orchestration layer instead of extending a reusable execution engine.

---

# Decision

The project adopts a dedicated Processing Framework as the execution layer of the Modern Data Platform.

Apache Airflow will be responsible exclusively for workflow orchestration.

All processing logic shall be implemented inside the Processing Framework.

Business pipelines must execute independently of any orchestration technology.

The orchestration layer becomes a client of the Processing Framework rather than its implementation.

---

# Architectural Vision

The Processing Framework becomes the central execution engine of the platform.

Every execution environment interacts with the framework using the same public API.

Future integrations should not require modifications to business pipelines.

```

```text
                    Apache Airflow
                           │
                           │
                           ▼
               Processing Framework
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
  SequentialExecutor  ParallelExecutor  SparkExecutor
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
                   Business Pipeline
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
    PostgreSQL         Kafka          Databricks
```

The framework is intentionally independent from any orchestration platform.

Airflow, Prefect, Dagster or future orchestrators should all interact with the same execution API.

---

# Architectural Goals

The Processing Framework is designed around the following goals.

## Separation of Concerns

Processing responsibilities must remain independent from orchestration responsibilities.

Scheduling, workflow management and execution monitoring belong to the orchestrator.

Pipeline execution belongs to the Processing Framework.

---

## Reusability

Business pipelines should be executable from different environments without modification.

Examples include:

- Apache Airflow
- Local execution
- CLI tools
- Automated tests
- Future orchestration platforms

---

## Extensibility

The architecture must support incremental evolution without requiring modifications to existing pipelines.

New execution strategies should be introduced through extension rather than modification.

Examples include:

- Retry policies
- Timeout policies
- Parallel executors
- Streaming executors
- Spark executors
- Additional storage engines

---

## Testability

Every processing component should be independently testable.

Business stages must execute without requiring Airflow, Kafka or external orchestration infrastructure.

Unit tests should validate business behavior independently from infrastructure concerns.

---

## Technology Independence

Business processing should not depend on:

- Apache Airflow
- Apache Spark
- Kafka
- Databricks
- Cloud providers

Infrastructure components remain replaceable while business pipelines remain stable.

---

## Long-Term Maintainability

As the project grows, the architecture should support:

- hundreds of stages
- dozens of pipelines
- multiple execution strategies
- multiple storage technologies
- multiple orchestration platforms

without requiring architectural redesign.

---

# Design Principles

The Processing Framework adopts the following architectural principles.

## Pipeline Immutability

Pipelines are immutable objects.

Once created, a pipeline definition cannot be modified.

Every configuration change produces a new pipeline instance.

Benefits include:

- thread safety
- deterministic execution
- predictable behavior
- easier testing

---

## Async First

The execution model is asynchronous by design.

Although some stages may internally perform synchronous operations, the public execution API remains asynchronous.

This decision avoids future breaking changes when introducing streaming, network operations or distributed execution.

---

## Composition over Inheritance

Framework capabilities should be composed through independent components rather than deep inheritance hierarchies.

Examples include:

- RetryPolicy
- TimeoutPolicy
- HookManager
- MetricsCollector
- WorkerPool

Each capability should evolve independently.

---

## Open/Closed Principle

The framework should be open for extension while remaining closed for modification.

New execution strategies should be implemented by introducing new components rather than changing existing implementations.

Examples include:

- new executors
- new retry strategies
- new timeout strategies
- new metrics exporters

without modifying existing pipeline definitions.

---

## Infrastructure Agnostic

Business processing must remain independent from infrastructure technologies.

A business stage should not know whether it is executed:

- by Airflow
- inside Kubernetes
- locally
- inside automated tests

Infrastructure concerns remain outside the business execution layer.

---

## Explicit Execution Model

Execution should always follow an explicit lifecycle.

The framework avoids hidden behavior.

Every execution step should be observable, measurable and extensible.


# Core Components

The Processing Framework is organized as a set of independent components with well-defined responsibilities.

Each component represents a single architectural concern and communicates with other components through explicit interfaces.

No component should assume implementation details of another component.

The overall architecture follows a layered execution model.

```text
                Processing Framework

                       │

       ┌───────────────┼────────────────┐

       ▼               ▼                ▼

   Pipeline        Executor         Observability

       │               │

       ▼               ▼

     Stages       Policies/Hooks

       │               │

       └───────────────┼───────────────┐

                       ▼               ▼

                 Worker Pool      Queue Manager

                       │

                       ▼

                Infrastructure Layer
```

The framework is intentionally modular.

Every major component can evolve independently while preserving the public execution contract.

---

# Component Overview

The framework is composed of the following core components.

| Component | Responsibility |
|------------|----------------|
| Pipeline | Defines the business workflow |
| PipelineBuilder | Creates immutable pipeline definitions |
| Executor | Coordinates pipeline execution |
| Stage | Represents a single processing step |
| ProcessingContext | Shared execution context |
| ProcessingResult | Execution outcome |
| Statistics | Execution metrics |
| RetryPolicy | Retry behavior |
| TimeoutPolicy | Timeout behavior |
| FallbackPolicy | Recovery behavior |
| HookManager | Lifecycle events |
| WorkerPool | Internal concurrency |
| QueueManager | Internal communication |
| MetricsCollector | Observability |

---

# Pipeline

A Pipeline represents a business process.

It contains no execution logic.

Its only responsibility is describing:

- stages
- execution order
- metadata
- configuration

A Pipeline is immutable.

Once created, its structure cannot change.

Instead of modifying an existing Pipeline, a new instance must be created.

This guarantees deterministic execution and prevents accidental runtime mutations.

---

# Pipeline Builder

Pipeline creation should occur through a dedicated Builder.

The Builder provides a fluent API for assembling pipeline definitions.

Example responsibilities include:

- adding stages
- configuring metadata
- validating pipeline structure
- creating immutable instances

The Builder is not responsible for executing pipelines.

---

# Executor

The Executor is the heart of the Processing Framework.

It coordinates every execution.

Responsibilities include:

- pipeline lifecycle
- stage execution
- statistics
- retry coordination
- timeout coordination
- hook invocation
- error propagation
- cancellation
- resource cleanup

The Executor never performs business processing.

Instead, it delegates work to Stages.

---

# Stage

A Stage represents the smallest executable processing unit.

Stages encapsulate business logic.

Examples include:

- reading a file
- validating data
- transforming records
- writing to storage
- publishing events

Stages should remain independent from orchestration technologies.

Every Stage receives a ProcessingContext and returns a ProcessingResult.

Stages must not communicate directly with each other.

All communication occurs through the shared ProcessingContext.

---

# Processing Context

The ProcessingContext represents the execution state shared by all Stages.

It replaces hidden global state with explicit execution data.

The Context evolves during execution.

Every Stage may enrich the Context by adding new information.

Example data includes:

- execution identifiers
- metadata
- datasets
- temporary values
- execution flags
- statistics
- shared resources

The Context should not contain business logic.

It only transports execution state.

---

# Processing Result

Every Stage produces a ProcessingResult.

The Result describes the execution outcome.

Typical information includes:

- execution status
- execution duration
- processed records
- warnings
- errors
- metadata

ProcessingResults are immutable.

They become part of the pipeline execution history.

---

# Execution Model

The framework follows a deterministic execution model.

Pipeline execution always follows the same lifecycle.

```text
Pipeline

↓

Executor

↓

Initialize Context

↓

Before Pipeline Hooks

↓

Execute Stages

↓

After Pipeline Hooks

↓

Finalize Statistics

↓

Return Result
```

Every execution follows this lifecycle.

No hidden execution paths exist.

---

# Stage Lifecycle

Each Stage follows its own lifecycle.

```text
Receive Context

↓

Before Stage Hooks

↓

Execute Business Logic

↓

Apply Policies

↓

Generate Result

↓

After Stage Hooks

↓

Return Updated Context
```

This lifecycle guarantees consistency across every Stage implementation.

---

# Execution Flow

The Executor controls the complete execution flow.

```text
Pipeline

↓

Executor

↓

Stage 1

↓

Update Context

↓

Stage 2

↓

Update Context

↓

Stage 3

↓

Update Context

↓

Pipeline Result
```

The Executor never manipulates business data directly.

It coordinates execution while Stages perform processing.

---

# State Management

The Processing Framework adopts explicit state management.

Execution state is always represented by the ProcessingContext.

No Stage should depend on:

- global variables
- singleton state
- hidden caches
- orchestrator-specific context

Every dependency required during execution must be explicitly available through the Context or dependency injection.

---

# Failure Model

Failures are treated as first-class execution events.

Errors are never silently ignored.

When a Stage fails, execution is delegated to the configured resilience policies.

The Executor remains responsible for coordinating failure handling.

Individual Stages remain focused exclusively on business processing.

This separation allows resilience strategies to evolve independently from business implementations.


# Executors

The Processing Framework delegates pipeline execution to specialized Executors.

An Executor defines **how** a pipeline is executed without changing **what** the pipeline does.

This separation allows the same business pipeline to execute using different execution strategies while preserving identical business behavior.

Business stages must remain completely unaware of the execution strategy.

The Executor is therefore responsible for:

- execution coordination
- lifecycle management
- cancellation
- resource allocation
- concurrency control
- resilience policy orchestration
- execution statistics

The Executor is **not** responsible for business processing.

---

# Execution Strategy

Execution strategy is an infrastructure concern.

Business pipelines should execute identically regardless of the selected Executor.

Future execution strategies may include:

- Sequential execution
- Parallel execution
- Distributed execution
- Spark execution
- Streaming execution

Pipeline definitions remain unchanged.

Only the execution engine changes.

---

# Sequential Executor

The Sequential Executor is the reference implementation of the framework.

Stages execute one after another.

```text
Stage 1

↓

Stage 2

↓

Stage 3

↓

Stage 4
```

Characteristics:

- deterministic
- predictable
- easier debugging
- simpler resource management

This executor should be the default execution strategy.

---

# Parallel Executor

The Parallel Executor executes independent stages concurrently.

Execution order is determined by dependency analysis rather than declaration order.

Example:

```text
           Stage 1

          /       \

         ▼         ▼

    Stage 2     Stage 3

          \       /

           ▼     ▼

            Stage 4
```

Only stages without execution dependencies may execute simultaneously.

Dependency resolution remains deterministic.

Parallel execution must never change business results.

---

# Executor Selection

Executors are interchangeable.

Pipeline definitions must never contain executor-specific logic.

Typical execution flow:

```text
Pipeline

↓

Executor Factory

↓

Selected Executor

↓

Pipeline Execution
```

This design allows future executors to be introduced without changing pipeline definitions.

---

# Worker Pool

The Worker Pool manages concurrent execution resources.

Instead of creating threads or tasks on demand, execution workers are reused throughout the pipeline lifecycle.

Responsibilities include:

- worker allocation
- worker recycling
- concurrency limits
- execution scheduling
- workload balancing

Business Stages never interact directly with Workers.

Workers remain an internal infrastructure concern.

---

# Worker Lifecycle

Workers follow a managed lifecycle.

```text
Create Worker

↓

Idle

↓

Receive Task

↓

Execute Stage

↓

Return Result

↓

Idle

↓

Shutdown
```

Workers should remain stateless.

Execution state belongs exclusively to the ProcessingContext.

---

# Queue Manager

The Queue Manager coordinates internal communication between execution components.

It is responsible for:

- pending stages
- completed stages
- failed stages
- dependency resolution
- execution ordering

The Queue Manager is an implementation detail.

Business pipelines remain unaware of its existence.

---

# Internal Execution Flow

The Worker Pool and Queue Manager cooperate during execution.

```text
Executor

↓

Queue Manager

↓

Worker Pool

↓

Worker

↓

Stage

↓

Processing Context

↓

Result

↓

Queue Manager
```

This architecture allows concurrency without coupling business logic to execution infrastructure.

---

# Resilience Model

Failures are expected events.

The Processing Framework treats resilience as a dedicated architectural concern rather than embedding recovery logic inside business stages.

Every resilience mechanism operates outside business code.

Stages should express business behavior only.

Recovery strategies belong to the execution layer.

---

# Retry Policy

Retries are coordinated by the Executor.

Stages never implement retry loops.

The Retry Policy determines:

- retry eligibility
- retry limits
- retry intervals
- retry backoff strategy

Example lifecycle:

```text
Stage

↓

Failure

↓

Retry Policy

↓

Retry

↓

Success

or

↓

Failure
```

Retry behavior must remain configurable.

---

# Timeout Policy

Execution time is explicitly controlled.

Every Stage may define execution limits.

When a timeout occurs:

```text
Stage

↓

Execution Timeout

↓

Cancel Execution

↓

Invoke Failure Policy
```

Timeout management belongs to the Executor.

Stages should remain unaware of timeout enforcement.

---

# Fallback Policy

Certain failures may be recoverable.

The Fallback Policy allows alternative execution paths without modifying business logic.

Examples include:

- secondary storage
- cached datasets
- backup services
- degraded execution

Fallback execution should remain transparent to the Stage implementation.

---

# Circuit Breaker

Repeated failures may indicate infrastructure instability.

The Circuit Breaker protects downstream systems by temporarily interrupting execution.

Typical lifecycle:

```text
Closed

↓

Failures

↓

Open

↓

Recovery Window

↓

Half Open

↓

Success

↓

Closed
```

Circuit Breakers operate independently from Retry Policies.

Retries handle transient failures.

Circuit Breakers protect external systems.

---

# Policy Pipeline

Execution policies are applied in a deterministic order.

```text
Receive Stage

↓

Retry Policy

↓

Timeout Policy

↓

Fallback Policy

↓

Circuit Breaker

↓

Execute Stage
```

Each policy addresses a single architectural concern.

Policies remain independently replaceable.

---

# Error Propagation

The framework follows explicit error propagation rules.

Failures are never silently ignored.

Every failure must result in one of the following outcomes:

- recovered
- propagated
- transformed
- cancelled

The execution engine remains responsible for coordinating these outcomes.

Business Stages should never decide how pipeline execution proceeds after failure.

---

# Design Rationale

Separating execution infrastructure from business processing provides several long-term advantages.

It allows:

- executor replacement
- independent resilience evolution
- infrastructure portability
- deterministic testing
- consistent execution lifecycle

Most importantly, it prevents business code from becoming coupled to execution mechanics, preserving the modularity of the Processing Framework as it grows.


# Hooks

Hooks provide extension points during pipeline execution without modifying the execution engine.

Hooks allow cross-cutting concerns to be implemented independently from business processing.

Typical use cases include:

- logging
- metrics
- auditing
- tracing
- notifications
- custom validation

Hooks should never contain business logic.

---

# Hook Lifecycle

The framework exposes hooks throughout the execution lifecycle.

```text
Pipeline Started

↓

Before Pipeline

↓

Before Stage

↓

After Stage

↓

Pipeline Completed

↓

Pipeline Failed
```

Each event is optional.

Framework components may subscribe only to the events they require.

---

# Hook Manager

The Hook Manager coordinates hook registration and invocation.

Responsibilities include:

- hook registration
- execution ordering
- asynchronous invocation
- error isolation

Failures inside Hooks must never affect business execution unless explicitly configured.

Hooks are considered auxiliary infrastructure.

---

# Observability

Observability is considered a first-class architectural concern.

The framework should expose execution information independently from the orchestration platform.

Observability includes:

- metrics
- logs
- traces
- execution statistics
- execution history

Business stages remain independent from observability technologies.

---

# Metrics

The framework should expose metrics describing pipeline execution.

Examples include:

Pipeline Metrics

- execution duration
- successful executions
- failed executions
- cancelled executions

Stage Metrics

- execution duration
- retries
- timeout count
- processed records

Infrastructure Metrics

- active workers
- queue length
- executor utilization

Metrics should remain technology agnostic.

Future exporters may include:

- Prometheus
- OpenTelemetry
- CloudWatch
- Azure Monitor
- Google Cloud Monitoring

without requiring modifications to business pipelines.

---

# Statistics

Execution Statistics represent the immutable summary of a pipeline execution.

Typical information includes:

- pipeline identifier
- execution identifier
- start time
- finish time
- duration
- stage count
- successful stages
- failed stages
- retry count
- timeout count
- processed records

Statistics are intended for reporting rather than operational monitoring.

---

# Logging

Logging provides chronological visibility into execution.

The framework should produce structured logs.

Log entries should contain contextual information including:

- execution id
- pipeline id
- stage id
- worker id
- timestamp
- severity

Business Stages should avoid infrastructure logging whenever possible.

Execution infrastructure remains responsible for lifecycle logging.

---

# Distributed Tracing

The architecture is designed to support distributed tracing.

Although tracing is optional, execution components should propagate execution identifiers throughout the pipeline lifecycle.

Future integrations may include:

- OpenTelemetry
- Jaeger
- Zipkin

without changing business code.

---

# Airflow Integration

Apache Airflow is adopted exclusively as the orchestration platform.

Airflow is not responsible for business execution.

Instead, Airflow invokes the Processing Framework using its public execution interface.

```text
Airflow DAG

↓

Python Operator

↓

Processing Framework

↓

Executor

↓

Business Pipeline
```

This separation allows pipelines to execute independently from Airflow.

---

# Responsibilities

The architectural responsibilities are intentionally separated.

| Component | Responsibility |
|------------|----------------|
| Airflow | Scheduling and orchestration |
| Processing Framework | Pipeline execution |
| Pipeline | Business workflow definition |
| Executor | Execution coordination |
| Stage | Business processing |
| ProcessingContext | Execution state |
| WorkerPool | Resource management |
| QueueManager | Execution coordination |
| Policies | Resilience |
| Hooks | Extension points |
| Metrics | Operational visibility |
| Statistics | Execution summary |

No responsibility should overlap another.

---

# Architectural Boundaries

The following concerns explicitly belong outside the Processing Framework.

The framework is **not** responsible for:

- workflow scheduling
- cron management
- DAG visualization
- infrastructure provisioning
- container orchestration
- cloud resource management

These responsibilities remain external.

Likewise, orchestration platforms should never contain business processing logic.

---

# Trade-offs

The adopted architecture intentionally increases initial complexity.

This additional complexity provides long-term benefits including:

- improved maintainability
- higher modularity
- infrastructure independence
- reusable business pipelines
- improved testability
- easier extensibility

The project prioritizes long-term architectural quality over short-term implementation simplicity.

---

# Alternatives Considered

## Business Logic Inside Airflow DAGs

Rejected.

Although simpler, this approach tightly couples business processing to the orchestration platform.

Business pipelines become difficult to reuse outside Airflow.

---

## Direct Spark Jobs

Rejected.

Apache Spark is an execution engine rather than a processing architecture.

The project requires an execution model capable of supporting multiple processing technologies.

---

## Prefect as Execution Framework

Rejected.

Prefect combines orchestration and execution responsibilities.

The project intentionally separates these concerns.

---

## Dagster Asset Model

Rejected.

Dagster provides a higher-level orchestration abstraction.

The objective of this project is to demonstrate the design of an internal execution framework rather than adopting another orchestration platform.

---

# Consequences

Positive consequences include:

- reusable processing architecture
- orchestration independence
- improved modularity
- easier testing
- cleaner separation of concerns
- extensible execution engine
- enterprise-inspired architecture

Negative consequences include:

- increased implementation effort
- additional architectural complexity
- larger maintenance surface

These trade-offs are considered acceptable for the objectives of this project.

---

# Future Extension Points

The architecture has been designed to evolve through extension.

Potential future capabilities include:

Execution

- Distributed Executor
- Spark Executor
- Ray Executor
- Dask Executor
- Streaming Executor

Observability

- OpenTelemetry
- Prometheus Exporter
- CloudWatch Exporter

Resilience

- Advanced Retry Policies
- Adaptive Backoff
- Dynamic Circuit Breakers

Execution

- Checkpointing
- Pipeline Resume
- Distributed State Management

None of these extensions require modifications to existing business pipelines.

---

# Final Architecture

```text
                           Apache Airflow
                                  │
                                  ▼
                     Processing Framework
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
     Pipeline                 Executor             Observability
         │                        │                        │
         ▼                        ▼                        ▼
      Stages                Policies/Hooks           Metrics
         │                        │                        │
         └──────────────┬─────────┴─────────┬──────────────┘
                        ▼                   ▼
                  Worker Pool        Queue Manager
                        │
                        ▼
                 Infrastructure Layer
                        │
      ┌─────────────────┼─────────────────┐
      ▼                 ▼                 ▼
 PostgreSQL         Kafka           Databricks
```

---

# Summary

The Processing Framework is the execution engine of the Modern Data Platform.

It provides a deterministic, extensible and technology-independent execution model capable of supporting multiple orchestration platforms, execution strategies and infrastructure technologies.

Apache Airflow orchestrates workflows.

The Processing Framework executes business pipelines.

This separation establishes a clear architectural boundary that allows the platform to evolve while preserving reusable business logic and maintaining long-term architectural consistency.
