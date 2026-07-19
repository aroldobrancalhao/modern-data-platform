# Modern Data Platform

<p align="center">

**A cloud-agnostic, event-driven Modern Data Platform built with open-source technologies and production-ready engineering practices.**

Design and implementation inspired by real-world enterprise data platforms.

</p>

---

## Overview

Modern Data Platform is an end-to-end Data Engineering project designed to demonstrate how production-grade data platforms are built.

The project covers the complete lifecycle of modern analytical data:

- Change Data Capture (CDC)
- Event Streaming
- Distributed Processing
- Lakehouse Architecture
- Data Modeling
- Infrastructure as Code
- Observability
- CI/CD

Rather than focusing on a single technology, this project emphasizes software engineering principles, modular architecture, and cloud portability.

---

# Architecture Goals

The platform was designed around a few fundamental principles.

- Cloud-agnostic architecture
- Event-driven communication
- Infrastructure as Code
- Modular design
- Provider-based abstractions
- Reproducible environments
- High testability
- Production-ready practices

More details are available in the Architecture Decision Records (ADRs).

---

# High-Level Architecture

```text
                 Source Systems
                        │
                        ▼
                 PostgreSQL
                        │
                        ▼
                 Debezium (CDC)
                        │
                        ▼
                  Apache Kafka
                        │
                        ▼
                Apache Airflow
                        │
                        ▼
              Platform Abstractions
                        │
        ┌───────────────┼────────────────┐
        ▼               ▼                ▼
    Storage         Compute         Messaging
        │               │                │
        ▼               ▼                ▼
      Amazon S3     Databricks       Kafka/MSK
                        │
                        ▼
                 Apache Spark
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
      Bronze         Silver          Gold
                        │
                        ▼
                       dbt
                        │
                        ▼
                Amazon Athena
                        │
                        ▼
                  Power BI
```

---

# Technology Stack

| Layer | Technology |
|--------|------------|
| Programming Language | Python 3.13 |
| Database | PostgreSQL |
| CDC | Debezium |
| Streaming | Apache Kafka |
| Workflow Orchestration | Apache Airflow |
| Distributed Processing | Apache Spark |
| Compute Platform | Databricks |
| Object Storage | Amazon S3 |
| Data Modeling | dbt |
| Query Engine | Amazon Athena |
| Visualization | Power BI |
| Infrastructure as Code | Terraform |
| Containers | Docker |
| Version Control | GitHub |

---

# Project Structure

```text
modern-data-platform/

├── docs/
│   ├── architecture/
│   ├── diagrams/
│   ├── guides/
│   └── roadmap/
│
├── infrastructure/
│   ├── terraform/
│   └── environments/
│
├── src/
│   ├── analytics/
│   ├── cloud/
│   ├── common/
│   ├── ingestion/
│   ├── orchestration/
│   ├── platform/
│   ├── processing/
│   ├── quality/
│   └── streaming/
│
├── simulator/
├── notebooks/
├── dbt/
├── docker/
├── tests/
└── scripts/
```

---

# Repository Modules

## Platform

Infrastructure-independent abstractions.

Examples:

- Storage
- Compute
- Messaging
- Monitoring
- Catalog
- Security

---

## Cloud

Provider implementations.

Examples:

- AWS
- Azure
- Google Cloud
- Local

---

## Ingestion

Responsible for collecting data from external systems.

Examples:

- CDC
- APIs
- Batch Files

---

## Streaming

Responsible for asynchronous communication.

Examples:

- Kafka Producers
- Kafka Consumers
- Event Serialization

---

## Processing

Responsible for distributed processing.

Examples:

- Bronze Layer
- Silver Layer
- Gold Layer

---

## Quality

Responsible for validating data quality.

Future integrations include:

- Great Expectations
- Custom Validators

---

## Orchestration

Workflow management using Apache Airflow.

---

## Analytics

Analytical assets and semantic models.

---

# Data Flow

```text
Simulator

↓

PostgreSQL

↓

Debezium

↓

Kafka

↓

Airflow

↓

S3

↓

Spark

↓

Bronze

↓

Silver

↓

Gold

↓

dbt

↓

Athena

↓

Power BI
```

---

# Cloud Strategy

The platform follows a capability-based architecture.

Business logic never depends directly on cloud providers.

| Capability | AWS | Azure | GCP |
|------------|-----|--------|-----|
| Storage | S3 | ADLS Gen2 | GCS |
| Compute | Databricks / EMR | Databricks / Synapse | Databricks / Dataproc |
| Messaging | Kafka / MSK | Event Hubs | Pub/Sub |
| Monitoring | CloudWatch | Azure Monitor | Cloud Monitoring |
| Secrets | Secrets Manager | Key Vault | Secret Manager |

Provider-specific implementations are isolated behind platform contracts.

---

# Development Principles

- Infrastructure as Code
- Cloud Agnostic
- Provider Pattern
- Layered Architecture
- Dependency Injection
- Type Safety
- Automated Testing
- Continuous Integration

---

# Quick Start

## Clone the repository

```bash
git clone https://github.com/your-user/modern-data-platform.git

cd modern-data-platform
```

## Install dependencies

```bash
poetry install
```

## Start local infrastructure

```bash
docker compose up -d
```

The local environment includes:

- PostgreSQL
- Kafka
- Debezium
- Airflow
- MinIO
- Spark

---

# Documentation

Architecture documentation is located in:

```text
docs/architecture/
```

Current ADRs:

- ADR-000 – Architecture Principles
- ADR-001 – Platform Architecture
- ADR-002 – Platform Contracts
- ADR-003 – Cloud Strategy
- ADR-004 – Repository Structure
- ADR-005 – Development Standards

---

# Project Roadmap

## Phase 1 — Foundation

- Repository Structure
- Docker Environment
- Terraform Foundation

## Phase 2 — CDC

- PostgreSQL
- Debezium
- Kafka

## Phase 3 — Data Lake

- Bronze
- Silver
- Gold

## Phase 4 — Data Modeling

- dbt
- Athena
- Metrics

## Phase 5 — Analytics

- Dashboards
- Business KPIs

## Phase 6 — Observability

- Logging
- Metrics
- Alerts

## Phase 7 — CI/CD

- GitHub Actions
- Automated Testing
- Deployment

---

# Future Improvements

Planned enhancements include:

- Azure implementation
- Google Cloud implementation
- Apache Iceberg
- Delta Lake
- OpenLineage
- DataHub
- Kubernetes deployment
- Feature Store
- Machine Learning pipelines

---

# Contributing

Contributions are welcome.

Please read the contributing guidelines before submitting issues or pull requests.

---

# License

This project is licensed under the MIT License.

See the LICENSE file for details.

---

# Acknowledgements

This project was inspired by modern data engineering practices and the architecture of enterprise-grade data platforms.

Special thanks to the open-source community behind:

- Apache Airflow
- Apache Kafka
- Apache Spark
- dbt
- Terraform
- Docker
- Debezium