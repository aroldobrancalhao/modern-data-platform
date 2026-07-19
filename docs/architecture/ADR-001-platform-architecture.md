# ADR-001: Platform Architecture

- **Status:** Accepted
- **Date:** 2026-07-19
- **Decision Makers:** Project Maintainers

---

# Context

Modern data platforms must support multiple data sources, processing engines, orchestration tools, and cloud providers while remaining maintainable over time.

Many data projects become tightly coupled to a specific cloud provider or orchestration framework, making future evolution expensive.

To avoid these limitations, this project adopts a layered architecture that separates business capabilities from infrastructure concerns.

This document defines the logical architecture of the Modern Data Platform.

---

# Decision

The platform adopts a layered, modular, event-driven architecture.

Each layer has a well-defined responsibility and communicates with other layers through explicit interfaces.

Business capabilities must never depend directly on cloud implementations.

Cloud providers remain implementation details.

---

# High-Level Architecture

```
                        +---------------------+
                        |     Simulator       |
                        +----------+----------+
                                   |
                                   v
                        +---------------------+
                        |    PostgreSQL       |
                        +----------+----------+
                                   |
                                   v
                        +---------------------+
                        |      Debezium       |
                        +----------+----------+
                                   |
                                   v
                        +---------------------+
                        |       Kafka         |
                        +----------+----------+
                                   |
                                   v
                        +---------------------+
                        |      Airflow        |
                        +----------+----------+
                                   |
                                   v
                     +-----------------------------+
                     |        Platform Layer       |
                     +-----------------------------+
                        |       |        |
                        |       |        |
             +----------+       |        +-----------+
             |                  |                    |
             v                  v                    v
      Storage Provider   Compute Provider   Messaging Provider
             |                  |                    |
             +------------------+--------------------+
                                |
                                v
                        +---------------------+
                        |     Databricks      |
                        +----------+----------+
                                   |
                    +--------------+--------------+
                    |              |              |
                    v              v              v
                 Bronze         Silver         Gold
                                   |
                                   v
                               dbt Models
                                   |
                                   v
                           Analytics & BI
```

---

# Architectural Layers

The platform is divided into independent layers.

Each layer owns a single responsibility.

---

## Source Layer

Responsible for generating or receiving data.

Examples:

- PostgreSQL
- APIs
- Files
- ERP systems
- CRM systems

Responsibilities:

- Produce operational data
- Persist transactional information

Not responsible for:

- orchestration
- analytics
- transformations

---

## Capture Layer

Responsible for detecting data changes.

Current implementation:

- Debezium

Responsibilities:

- Capture Change Data Capture (CDC)
- Publish change events

The Capture Layer should remain unaware of downstream consumers.

---

## Messaging Layer

Responsible for transporting events.

Current implementation:

- Apache Kafka

Responsibilities:

- Event delivery
- Event durability
- Loose coupling

The Messaging Layer must not contain business logic.

---

## Orchestration Layer

Responsible for coordinating platform activities.

Current implementation:

- Apache Airflow

Responsibilities:

- Schedule workflows
- Trigger processing
- Monitor execution
- Coordinate dependencies

Not responsible for:

- transforming datasets
- cloud implementations
- business rules

---

## Platform Layer

The Platform Layer is the heart of the architecture.

Every external dependency must be abstracted through this layer.

Responsibilities include:

- Storage abstraction
- Compute abstraction
- Configuration
- Security
- Monitoring
- Metadata
- Catalog access

The Platform Layer isolates infrastructure from business logic.

---

## Processing Layer

Responsible for data transformation.

Current implementation:

- Databricks
- Apache Spark

Responsibilities:

- ETL
- ELT
- Aggregations
- Data enrichment
- Validation
- Data quality

Processing must remain independent of cloud providers.

---

## Analytics Layer

Responsible for serving analytical datasets.

Components include:

- Gold Layer
- dbt
- Athena
- Power BI

Responsibilities:

- Business metrics
- Reporting
- Dashboards
- Self-service analytics

---

# Medallion Architecture

The project adopts the Medallion Architecture.

---

## Bronze Layer

Purpose:

Persist raw data.

Characteristics:

- Immutable
- Historical
- Minimal transformations

Allowed operations:

- Schema normalization
- Metadata enrichment
- Technical validation

---

## Silver Layer

Purpose:

Create trusted datasets.

Characteristics:

- Clean
- Standardized
- Deduplicated
- Validated

Allowed operations:

- Type conversion
- Null handling
- Data quality
- Business validation
- Standardization

---

## Gold Layer

Purpose:

Business-ready datasets.

Characteristics:

- Aggregated
- Optimized
- Analytics-ready

Consumers:

- BI tools
- Machine Learning
- Data Science
- Business users

---

# Platform Modules

The project is organized around platform capabilities.

```
src/platform/

    config/

    storage/

    compute/

    messaging/

    monitoring/

    catalog/

    security/

    providers/
```

Each module exposes interfaces rather than cloud implementations.

---

# Storage Abstraction

Business code must never access object storage directly.

Instead of:

```
S3Client(...)
```

Business code should use:

```
platform.storage.write(...)
```

The provider determines whether the destination is:

- Amazon S3
- Azure Data Lake
- Google Cloud Storage

---

# Compute Abstraction

Business code should never execute provider-specific jobs.

Instead:

```
platform.compute.run(...)
```

Supported implementations may include:

- Databricks
- EMR
- Synapse
- Dataproc

---

# Messaging Abstraction

Messaging services remain interchangeable.

Business code depends on:

```
MessagingProvider
```

Possible implementations:

- Kafka
- Event Hubs
- Pub/Sub

---

# Configuration

Application configuration must be centralized.

Configuration sources include:

- Environment Variables
- Configuration Files
- Secret Managers

Configuration must never be hardcoded.

---

# Dependency Direction

Dependencies always point inward.

```
Infrastructure

↓

Providers

↓

Platform

↓

Business Logic

↓

Analytics
```

Business logic never depends directly on infrastructure.

---

# Repository Organization

The repository is divided by responsibility.

```
src/

    platform/

    ingestion/

    streaming/

    processing/

    quality/

    simulator/

    common/
```

Repository organization is detailed in ADR-003.

---

# Scalability

The architecture supports horizontal scaling through:

- Stateless services
- Event-driven communication
- Distributed compute
- Object storage
- Independent modules

---

# Extensibility

Future additions should require new implementations rather than architectural changes.

Examples:

Adding Azure should introduce:

```
AzureStorageProvider
```

without changing:

- Airflow
- Business Logic
- Processing

The same applies to future cloud providers.

---

# Trade-offs

Advantages:

- Cloud portability
- Testability
- Maintainability
- Loose coupling
- High modularity
- Easier onboarding

Disadvantages:

- Additional abstraction layers
- More interfaces
- Slightly higher learning curve

The project intentionally prioritizes long-term maintainability over short-term simplicity.

---

# Consequences

The architecture establishes a clear separation between:

- Infrastructure
- Platform
- Processing
- Analytics

Every future feature should integrate into one of these layers without violating their responsibilities.

---

# Related ADRs

- ADR-000 – Architecture Principles
- ADR-002 - Platform Contracts
- ADR-003 - Cloud Strategy
- ADR-004 - Repository Structure
- ADR-005 - Development Standards