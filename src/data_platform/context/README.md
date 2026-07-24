# Context Module

## Overview

The Context module contains the execution context shared across the entire
Data Platform.

Instead of passing several independent parameters between services,
all execution information is grouped into dedicated context objects.

This keeps services simple, improves readability and allows future
extensions without changing service interfaces.

---

# Architecture

```
ExecutionContext
│
├── ExecutionMetadata
│
├── Environment
├── ExecutionMode
└── ExecutionSource

PipelineContext
│
├── Dataset
├── PipelineStage
└── PipelineStatus
```

---

# ExecutionMetadata

ExecutionMetadata stores information that uniquely identifies an execution.

Current responsibilities:

- Execution identifier
- Correlation identifier
- Execution start time

Typical example:

```python
ExecutionMetadata(
    execution_id=UUID(...),
    correlation_id=UUID(...),
    started_at=datetime.utcnow(),
)
```

This information is immutable during execution.

---

# ExecutionContext

ExecutionContext represents the environment in which a service is executed.

It does **not** contain business data.

Instead, it describes **how** the execution is running.

Current information includes:

- execution metadata
- environment
- execution mode
- execution source

Example:

```python
ExecutionContext(
    metadata=metadata,
    environment=Environment.DEVELOPMENT,
    execution_mode=ExecutionMode.BATCH,
    execution_source=ExecutionSource.AIRFLOW,
)
```

Every business service receives the same ExecutionContext.

Examples:

```
BronzeService

SilverService

GoldService
```

The services do not know who invoked them.

Possible callers include:

- Apache Airflow
- Kafka Consumers
- REST APIs
- Command Line Interface
- Unit Tests

This keeps business logic independent from orchestration.

---

# PipelineContext

PipelineContext contains information specific to pipeline execution.

Unlike ExecutionContext, this object describes **what** is being processed.

Current responsibilities:

- Dataset
- Pipeline Stage
- Pipeline Status

Example:

```python
PipelineContext(
    dataset="orders",
    stage=PipelineStage.BRONZE,
)
```

As processing evolves, the status can change:

```
CREATED

↓

RUNNING

↓

SUCCESS
```

or

```
CREATED

↓

RUNNING

↓

FAILED
```

---

# Why separate ExecutionContext and PipelineContext?

Both concepts describe different aspects of execution.

ExecutionContext answers:

- Where is the execution running?
- Who started it?
- Is it Batch or Streaming?
- Which environment?

PipelineContext answers:

- Which dataset is being processed?
- Which stage is executing?
- What is the current status?

Keeping these concerns separated follows the Single Responsibility Principle.

---

# Design Principles

The Context module follows these principles:

- Immutable execution metadata
- Small and focused models
- Storage independent
- Orchestration independent
- Reusable across all platform components

Future modules such as Airflow, Kafka, Observability and Data Quality will
reuse these context objects.