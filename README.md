# Modern Data Platform

**Status:** Under Development

Modern Data Platform is an end-to-end Data Engineering project created to simulate how modern organizations build and operate analytical data platforms.

The project follows a cloud-agnostic architecture and demonstrates the complete data lifecycle, from transactional systems to business intelligence, using technologies commonly adopted in enterprise environments.

The initial implementation targets AWS, while the architecture is designed to support additional cloud providers with minimal changes.

---

## Objectives

This project aims to:

- Build a modern end-to-end data platform.
- Implement batch and streaming data pipelines.
- Capture transactional changes using Change Data Capture (CDC).
- Build a Lakehouse architecture following the Medallion pattern.
- Model analytical data using Star Schema.
- Apply DataOps and Analytics Engineering best practices.
- Design a cloud-agnostic architecture that can evolve across multiple cloud providers.

---

## Project Scope

The platform covers the complete analytical data lifecycle, including:

- Transaction simulation
- Change Data Capture (CDC)
- Event streaming
- Batch processing
- Lakehouse architecture
- Analytics Engineering
- Dimensional modeling
- Business Intelligence
- Data Quality
- Monitoring and Observability
- Infrastructure as Code

---

## High-Level Architecture

> A detailed architecture diagram will be added as the project evolves.

```text
Transaction Simulator
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
 Amazon S3
        │
        ▼
 Databricks (PySpark)
        │
        ▼
 Bronze
        │
        ▼
 Silver
        │
        ▼
 dbt Core
        │
        ▼
 Gold (Star Schema)
        │
        ▼
 Amazon Athena
        │
        ▼
 Power BI
```

---

## Technology Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.12 |
| Database | PostgreSQL |
| Change Data Capture | Debezium |
| Streaming Platform | Apache Kafka |
| Workflow Orchestration | Apache Airflow |
| Data Processing | Apache Spark / PySpark |
| Lakehouse | Delta Lake |
| Analytics Engineering | dbt Core |
| Cloud Storage | Amazon S3 |
| Metadata Catalog | AWS Glue |
| Query Engine | Amazon Athena |
| Business Intelligence | Power BI |
| Data Quality | Great Expectations, dbt Tests |
| Monitoring | Prometheus, Grafana |
| Containerization | Docker, Docker Compose |
| Infrastructure as Code | Terraform |
| Version Control | Git, GitHub |

---

## Architecture Principles

The platform is designed around the following principles:

- Cloud-agnostic architecture
- Event-driven architecture
- Lakehouse architecture
- Medallion architecture
- ELT pipelines
- Separation of concerns
- Infrastructure as Code
- Data Quality by default
- Observability by design
- Modular and extensible components

---

## Planned Capabilities

### Data Platform

- Transaction simulator
- Batch data ingestion
- Change Data Capture (CDC)
- Kafka event streaming
- Lakehouse implementation
- Bronze, Silver and Gold layers
- Delta Lake
- Star Schema
- Data Marts

### Data Quality

- Data validation
- Data profiling
- Schema validation
- dbt Tests
- Great Expectations

### Reliability

- Retry mechanisms
- Dead Letter Queue (DLQ)
- Quarantine layer

### Operations

- Monitoring
- Logging
- Metrics
- Alerting
- CI/CD pipelines
- Infrastructure as Code

---

## Repository Structure

```text
modern-data-platform/

├── docs/
├── infrastructure/
├── src/
├── dbt/
├── dashboards/
├── datasets/
├── notebooks/
├── scripts/
├── tests/
└── README.md
```

---

## Roadmap

### Phase 1 — Foundation

- Development environment
- Project structure
- Docker
- PostgreSQL
- Transaction simulator

### Phase 2 — Streaming Platform

- Debezium
- Apache Kafka
- Apache Airflow
- CDC pipelines

### Phase 3 — Lakehouse

- AWS integration
- Amazon S3
- Databricks
- Bronze layer
- Silver layer

### Phase 4 — Analytics

- dbt
- Gold layer
- Star Schema
- Data Marts
- Amazon Athena
- Power BI

### Phase 5 — Platform Operations

- Data Quality
- Monitoring
- Observability
- Infrastructure as Code
- GitHub Actions
- CI/CD

---

## Cloud Providers

The platform is designed to support multiple cloud providers through a provider abstraction layer.

Current implementation:

- AWS

Planned support:

- Microsoft Azure
- Google Cloud Platform

---

## Project Status

This project is actively being developed.

New features, architecture decisions and documentation will be added incrementally as the platform evolves.

## License

This project is licensed under the MIT License.