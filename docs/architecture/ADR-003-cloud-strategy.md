# ADR-003: Cloud Strategy

- **Status:** Accepted
- **Date:** 2026-07-19
- **Decision Makers:** Project Maintainers

---

# Context

Cloud providers offer similar capabilities through different services, APIs, and operational models.

Many data platforms become tightly coupled to a specific provider by directly consuming proprietary services throughout the application.

This project adopts a capability-based cloud strategy to maximize portability, maintainability, and extensibility.

Cloud providers are implementation details rather than architectural decisions.

---

# Decision

The Modern Data Platform shall be cloud-agnostic.

Business logic, orchestration workflows, notebooks, and processing pipelines must depend only on platform contracts.

Cloud-specific implementations are isolated behind provider adapters.

---

# Objectives

The cloud strategy aims to:

- Minimize vendor lock-in
- Promote portability
- Simplify cloud migrations
- Encourage modularity
- Reduce infrastructure coupling
- Support multiple deployment targets

---

# Capability-Based Architecture

The platform is organized around capabilities instead of cloud vendors.

```
                  Platform

                     │

 ┌──────────┬─────────────┬─────────────┬──────────────┐

 Storage   Compute    Messaging     Monitoring

     │          │            │             │

     ▼          ▼            ▼             ▼

 AWS        Azure        GCP        Local
```

Every capability defines a contract.

Providers implement those contracts.

---

# Supported Cloud Providers

The platform is initially implemented on AWS.

The architecture is designed to support:

- Amazon Web Services
- Microsoft Azure
- Google Cloud Platform

without architectural changes.

---

# Capability Mapping

| Platform Capability | AWS | Azure | Google Cloud |
|----------------------|-----|--------|--------------|
| Object Storage | Amazon S3 | Azure Data Lake Storage Gen2 | Google Cloud Storage |
| Distributed Compute | Databricks / EMR | Databricks / Synapse | Databricks / Dataproc |
| Messaging | Kafka / MSK | Event Hubs (Kafka API) | Pub/Sub / Kafka |
| Metadata Catalog | Unity Catalog / AWS Glue | Unity Catalog | Unity Catalog / Dataplex |
| Secrets | Secrets Manager | Key Vault | Secret Manager |
| Monitoring | CloudWatch | Azure Monitor | Cloud Monitoring |
| Identity | IAM | Managed Identity | Workload Identity |
| Infrastructure | Terraform | Terraform | Terraform |

The business layer never depends on these services directly.

---

# Provider Architecture

```
Business Logic

        │

        ▼

StorageProvider

        │

 ┌──────┴──────────┐

 │                 │

S3Provider   ADLSProvider

                    │

             GCSProvider
```

Every provider implements the same contract.

---

# Deployment Strategy

The platform supports multiple deployment environments.

```
Local Development

↓

Docker

↓

Cloud Environment

↓

Production
```

Environment differences are resolved through configuration rather than code changes.

---

# Infrastructure Strategy

Infrastructure is managed exclusively through Terraform.

Every provider exposes its own implementation while sharing the same architectural structure.

Example:

```
terraform/

    modules/

    providers/

        aws/

        azure/

        gcp/
```

Each provider reuses common modules whenever possible.

---

# Storage Strategy

Business code interacts only with the Storage Provider.

Forbidden:

```
import boto3

client = boto3.client(...)
```

Preferred:

```
storage.write(...)

storage.read(...)
```

This abstraction enables transparent migration between storage services.

---

# Compute Strategy

Distributed processing is abstracted behind the Compute Provider.

Business logic should not know whether processing occurs on:

- Databricks
- EMR
- Synapse
- Dataproc

Execution details remain infrastructure concerns.

---

# Messaging Strategy

Messaging services expose identical behavior through platform contracts.

Supported implementations include:

- Apache Kafka
- Amazon MSK
- Azure Event Hubs (Kafka Protocol)
- Google Pub/Sub

Business services publish events without provider awareness.

---

# Metadata Strategy

Metadata services remain replaceable.

Possible implementations:

- Unity Catalog
- AWS Glue
- Hive Metastore
- Dataplex

Processing components consume metadata through the Catalog Contract.

---

# Authentication Strategy

Authentication mechanisms differ across providers.

The platform hides these differences behind the Identity Contract.

Business code never manipulates provider credentials directly.

Preferred mechanisms include:

- IAM Roles
- Managed Identity
- Workload Identity

---

# Secrets Management

Sensitive information must never be stored inside source code.

Secrets are retrieved dynamically through the Secrets Provider.

Examples include:

- Database credentials
- API keys
- Service tokens
- Encryption keys

---

# Monitoring Strategy

Monitoring follows an observability-first approach.

Capabilities include:

- Structured logging
- Metrics
- Distributed tracing
- Pipeline monitoring
- Health checks

Telemetry providers remain interchangeable.

---

# Local Development

Local execution should closely resemble production.

The recommended local stack includes:

- Docker
- PostgreSQL
- Kafka
- Debezium
- Airflow
- MinIO
- Local Spark

Cloud resources should only be required when strictly necessary.

---

# Multi-Cloud Readiness

Supporting a new cloud provider should require:

1. Implementing provider contracts
2. Creating Terraform provider modules
3. Adding configuration
4. Registering providers

Business logic must remain unchanged.

---

# Vendor Lock-In Policy

The platform intentionally avoids architectural dependence on proprietary services.

Cloud-native services are acceptable provided they remain behind platform contracts.

Replacing a provider should not require changes to:

- Airflow DAGs
- Spark jobs
- Business logic
- Platform services

---

# Trade-offs

Advantages

- Multi-cloud architecture
- Reduced vendor lock-in
- Better portability
- Simplified testing
- Long-term maintainability

Disadvantages

- Additional abstraction
- More provider implementations
- Slightly larger codebase

These trade-offs are acceptable considering the long-term benefits.

---

# Future Evolution

Future provider implementations may include:

- Oracle Cloud Infrastructure
- Alibaba Cloud
- IBM Cloud
- On-Premises deployments
- Kubernetes-native storage providers

The architecture should evolve by extending provider implementations rather than modifying business logic.

---

# Related ADRs

- ADR-000 – Architecture Principles
- ADR-001 – Platform Architecture
- ADR-002 – Platform Contracts
- ADR-004 – Repository Structure
- ADR-005 – Development Standards