# ADR-006: Platform Capability Model

- Status: Accepted
- Date: YYYY-MM-DD

## Context

The Modern Data Platform is designed to be cloud-agnostic.

The goal is to allow infrastructure providers (AWS, Azure, GCP, Local)
to be replaced with minimal impact on orchestration, processing,
business logic, or notebooks.

The project follows a capability-driven architecture instead of a
cloud-driven architecture.

This means application code depends on platform capabilities rather than
cloud-specific SDKs.

## Decision

The platform will expose a fixed set of capabilities.

Each capability defines a contract.

Concrete implementations are provided by providers.

```
Application
        │
        ▼
Platform Capability
        │
        ▼
Provider
        │
        ▼
Cloud Service
```

The Platform Layer will never import cloud SDKs directly.

Cloud-specific implementations belong exclusively to Providers.

## Platform Capabilities

The platform exposes the following capabilities.

- Configuration
- Storage
- Compute
- Messaging
- Catalog
- Query
- Data Quality
- Monitoring
- Notification
- Secrets
- Identity

Each capability defines:

- Interface
- Types
- Exceptions
- Configuration
- Provider Registration

## Provider Model

Providers implement one or more capabilities.

Example:

AWS

- Storage → Amazon S3
- Catalog → Glue Catalog
- Query → Athena

Databricks

- Compute

Azure

- Storage → ADLS
- Catalog → Unity Catalog

GCP

- Storage → GCS
- Query → BigQuery

## Registry

A Platform Registry is responsible for resolving active providers.

Application code never instantiates providers directly.

Instead it requests capabilities.

Example

Platform.storage()

Platform.compute()

Platform.catalog()

The registry selects the configured provider.

## Responsibilities

Platform Layer

- Contracts
- Types
- Provider Registry
- Configuration
- Exceptions

Providers

- Cloud SDKs
- Authentication
- Service-specific implementation

Application

- Business logic
- Orchestration
- Processing

Application code must never reference cloud SDKs directly.

## Consequences

Advantages

- Cloud portability
- Testability
- Separation of concerns
- Stable architecture
- Easy provider replacement

Trade-offs

- Slightly more abstraction.
- Initial implementation effort is higher.

The long-term maintenance cost is significantly lower.