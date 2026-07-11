# Architecture

## Overview

Modern Data Platform is an end-to-end Data Engineering platform designed to demonstrate how modern analytical platforms are built using cloud-native technologies.

The platform processes transactional data from operational systems and transforms it into analytical datasets that can be consumed by Business Intelligence tools.

The first implementation targets AWS, while the architecture is designed to support additional cloud providers in the future.

---

## Architecture Overview

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
                Bronze → Silver → Gold
                            │
                            ▼
                        dbt Core
                            │
                            ▼
                     Amazon Athena
                            │
                            ▼
                        Power BI
```

---

## Data Flow

The platform follows the complete analytical data lifecycle.

1. A transaction is created by the simulator.
2. The transaction is stored in PostgreSQL.
3. Debezium captures database changes using Change Data Capture (CDC).
4. Events are published to Apache Kafka.
5. Airflow orchestrates batch workflows.
6. Raw data is stored in Amazon S3.
7. Databricks processes the data using PySpark.
8. Data is transformed following the Medallion Architecture.
9. dbt creates analytical models using Star Schema.
10. Athena exposes the datasets for querying.
11. Power BI consumes the analytical data.

---

## Architecture Principles

The platform is based on the following principles:

- Cloud-agnostic design
- Event-driven architecture
- Lakehouse architecture
- Medallion architecture
- ELT pipelines
- Infrastructure as Code
- Data Quality
- Observability

---

## Main Components

| Component | Responsibility |
|-----------|----------------|
| PostgreSQL | Transactional database |
| Debezium | Change Data Capture |
| Kafka | Event streaming |
| Airflow | Workflow orchestration |
| Amazon S3 | Data Lake storage |
| Databricks | Distributed data processing |
| dbt | Analytical transformations |
| Athena | SQL query engine |
| Power BI | Business Intelligence |

---

## Current Status

The platform is under active development.

Each component will be implemented incrementally while maintaining a working and documented architecture.