# Modern Data Platform Architecture

## Overview

Modern Data Platform is an end-to-end Data Engineering platform designed to demonstrate how modern analytical platforms are built using cloud-native technologies, Event-Driven Architecture and Lakehouse principles.

The platform simulates a complete production-grade environment, starting from transactional systems and ending with curated analytical datasets consumed by Business Intelligence tools.

Rather than demonstrating isolated technologies, the project focuses on how each component interacts within a modern analytical ecosystem.

The platform implements the complete analytical lifecycle, including transactional processing, Change Data Capture (CDC), event streaming, workflow orchestration, distributed processing, data governance, semantic modeling, analytical querying, observability and business intelligence.

The first implementation targets Amazon Web Services (AWS), while maintaining a cloud-agnostic architecture that can be adapted to Azure or Google Cloud with minimal infrastructure changes.

The project follows modern Data Engineering practices and demonstrates practical experience with technologies frequently required by enterprise environments.

---

# Objectives

The primary objective of this platform is to simulate a production-ready analytical architecture used by modern organizations.

The project demonstrates practical implementation of:

- Event-Driven Architecture
- Change Data Capture (CDC)
- Workflow Orchestration
- Data Lake
- Delta Lake
- Lakehouse Architecture
- Medallion Architecture
- Enterprise Data Warehouse
- Semantic Layer
- Data Governance
- Data Quality
- Distributed Processing
- Infrastructure as Code
- Cloud Architecture
- Business Intelligence
- Observability

Each technology is responsible only for the tasks it was designed to perform, following the principle of separation of responsibilities.

---

# High-Level Architecture

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
                          Kafka
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
        Batch Processing       Streaming Processing
        (Airflow)              (Structured Streaming)
                │                       │
                └───────────┬───────────┘
                            │
                            ▼
                 Amazon S3 (Data Lake)
                            │
                            ▼
               Databricks (PySpark Engine)
                            │
                            ▼
                     Delta Lake (Bronze Tables)
                            │
                            ▼
                    Delta Lake (Silver Tables)
                            │
                            ▼
                    Delta Lake (Gold Tables)
                            │
                            ▼
               dbt Core (Semantic Layer)
                            │
                            ▼
              AWS Glue Data Quality
                            │
                            ▼
              AWS Glue Data Catalog
                            │
                            ▼
                     Amazon Athena
                            │
                            ▼
                        Power BI


────────────────────────────────────────────────────────────

             Amazon CloudWatch (Observability)

      Logs • Metrics • Alarms • Monitoring
```

---

# Platform Layers

The platform is organized into independent architectural layers.

Each layer has a single responsibility and communicates with adjacent layers through well-defined interfaces.

The architecture consists of the following layers:

```text
Transactional Layer

        │

        ▼

Event Streaming Layer

        │

        ▼

Workflow Orchestration Layer

        │

        ▼

Data Lake

        │

        ▼

Lakehouse

        │

        ▼

Enterprise Data Warehouse

        │

        ▼

Semantic Layer

        │

        ▼

Analytics Layer

        │

        ▼

Visualization Layer
```

Each layer can evolve independently while preserving the overall architecture.

---

# Platform Technologies

| Layer | Technology |
|--------|------------|
| Transactional Layer | PostgreSQL |
| Change Data Capture | Debezium |
| Event Streaming | Apache Kafka |
| Workflow Orchestration | Apache Airflow |
| Data Lake | Amazon S3 |
| Distributed Processing | Databricks |
| Storage Layer | Delta Lake |
| Enterprise Data Warehouse | Gold Layer |
| Semantic Layer | dbt Core |
| Data Governance | AWS Glue Data Quality |
| Metadata Catalog | AWS Glue Data Catalog |
| Analytics | Amazon Athena |
| Visualization | Power BI |
| Observability | Amazon CloudWatch |

---

# Architecture Principles

The platform follows modern architectural principles adopted by enterprise data platforms.

## Event-Driven Architecture

Operational systems publish events instead of directly feeding analytical systems.

Every data modification becomes an immutable event.

---

## Cloud-Native Architecture

Infrastructure is designed specifically for cloud environments.

Every component can scale independently.

---

## Cloud-Agnostic Design

Business logic never depends directly on cloud-specific services.

Only the infrastructure layer changes between cloud providers.

---

## Infrastructure as Code

Cloud infrastructure is provisioned using Terraform.

Infrastructure becomes versioned, reproducible and auditable.

---

## Separation of Responsibilities

Each technology performs only the responsibilities for which it was designed.

No component accumulates responsibilities belonging to another layer.

---

## ELT Processing

Data is first loaded into the platform and transformed afterwards.

Original data is always preserved.

---

## Incremental Processing

Whenever possible, processing occurs incrementally.

Only new or modified data is processed.

---

## Data Immutability

Raw data is never modified.

Every transformation generates a new version of the dataset.

---

## Scalability

Every processing layer is designed to support horizontal scaling.

---

## Observability

Every critical component must expose logs, metrics and monitoring information.

---

## Governance

Data quality and metadata are validated before datasets become available for analytical consumption.

---

# Cloud Abstraction

The architecture is intentionally cloud-agnostic.

Business rules are completely independent of the cloud provider.

Only infrastructure services change between providers.

| Capability | AWS | Azure | Google Cloud |
|------------|-----|--------|--------------|
| Object Storage | Amazon S3 | Azure Data Lake Storage Gen2 | Google Cloud Storage |
| Distributed Processing | Databricks on AWS | Databricks on Azure | Databricks on GCP |
| Metadata Catalog | AWS Glue Catalog | Microsoft Purview | Dataplex |
| SQL Analytics | Amazon Athena | Synapse Analytics | BigQuery |
| Monitoring | Amazon CloudWatch | Azure Monitor | Cloud Monitoring |

The processing logic remains identical regardless of the selected cloud platform.

---

# End-to-End Data Flow

The platform processes data through multiple independent stages.

Each stage is responsible for a specific part of the analytical lifecycle.

```text
Transaction Generation

        │

        ▼

Transactional Database

        │

        ▼

Change Data Capture

        │

        ▼

Event Streaming

        │

        ▼

Workflow Orchestration

        │

        ▼

Data Lake

        │

        ▼

Lakehouse Processing

        │

        ▼

Enterprise Data Warehouse

        │

        ▼

Semantic Layer

        │

        ▼

Analytics

        │

        ▼

Business Intelligence
```

The following sections describe each stage of the platform in detail.

# Transactional Layer

## Overview

The Transactional Layer represents the operational environment of the platform.

Its primary responsibility is to simulate a real-world marketplace where business operations continuously generate transactional data.

This layer is completely independent from analytical workloads.

No reporting, aggregations or business intelligence queries are executed here.

Its only responsibility is supporting transactional operations (OLTP).

---

## Transaction Simulator

The platform starts with a transaction simulator.

The simulator behaves like a real marketplace application by continuously generating business events.

Instead of producing random records, the simulator maintains relationships between entities, preserving referential integrity across the entire database.

Examples of generated entities include:

- Customers
- Customer Addresses
- Sellers
- Categories
- Products
- Warehouses
- Inventories
- Inventory Movements
- Orders
- Order Items
- Payments
- Shipments
- Reviews

The simulator intentionally generates realistic business scenarios, including inventory updates, order creation, payment processing and shipment events.

This allows the downstream analytical platform to process data that closely resembles production workloads.

---

## Marketplace Database

The simulator persists all transactions into PostgreSQL.

PostgreSQL represents the system of record (Source of Truth).

Every application writes exclusively to PostgreSQL.

No analytical component writes directly into analytical datasets.

```text
Application

        │

        ▼

PostgreSQL
```

The transactional database contains normalized tables optimized for OLTP workloads.

Typical characteristics include:

- Highly normalized schema
- Referential integrity
- ACID transactions
- Foreign keys
- Unique constraints
- Indexes optimized for transactional access

The transactional database is never queried directly by reporting tools.

---

## OLTP Characteristics

The transactional database is optimized for operational workloads.

Characteristics include:

- Small transactions
- High write throughput
- Low latency
- Strong consistency
- Referential integrity
- Frequent INSERTs
- Frequent UPDATEs
- Frequent DELETEs

Analytical workloads are intentionally isolated from this database.

---

# Change Data Capture (CDC)

## Overview

The platform captures transactional changes using Change Data Capture (CDC).

Instead of periodically querying PostgreSQL for modified records, every database change is captured as an immutable event.

This approach minimizes database load while enabling near real-time data propagation.

---

## Debezium

Debezium continuously monitors PostgreSQL through Logical Replication.

It reads the PostgreSQL Write-Ahead Log (WAL) and converts database changes into structured events.

The application remains completely unaware that CDC is occurring.

```text
PostgreSQL

        │

Logical Replication (WAL)

        │

        ▼

Debezium
```

Debezium captures:

- INSERT
- UPDATE
- DELETE

Every captured operation becomes an event.

No polling mechanism is required.

---

## Event Structure

Each captured event contains:

- Before image
- After image
- Operation type
- Timestamp
- Transaction metadata
- Source information

Example:

```text
Operation

INSERT

↓

Before

null

↓

After

Customer

↓

Timestamp

2026-07-15T12:00:00Z
```

The complete history of database modifications becomes available to downstream consumers.

---

## Benefits of CDC

Using Change Data Capture provides several advantages:

- Near real-time synchronization
- Minimal database impact
- Immutable event history
- Transaction ordering
- Scalability
- Decoupled architecture

The transactional application remains completely independent from analytical processing.

---

# Event Streaming Layer

## Apache Kafka

Kafka is the central event streaming platform.

It receives every event generated by Debezium.

Kafka becomes the immutable event bus connecting operational systems with analytical systems.

```text
PostgreSQL

↓

Debezium

↓

Kafka
```

Kafka is responsible only for transporting events.

It never transforms data.

---

## Topics

Each database table is mapped to its own Kafka Topic.

Example:

```text
marketplace.customers

marketplace.customer_addresses

marketplace.products

marketplace.orders

marketplace.order_items

marketplace.payments

marketplace.shipments

marketplace.inventory_movements

marketplace.reviews
```

This design allows consumers to subscribe only to the datasets they require.

---

## Event Retention

Kafka stores events for a configurable retention period.

Consumers may replay historical events whenever necessary.

Typical use cases include:

- Pipeline recovery
- Backfilling historical data
- Reprocessing datasets
- Testing new consumers

Kafka acts as the immutable history of platform events.

---

## Producer

Debezium is the only producer in the current architecture.

```text
PostgreSQL

↓

Debezium

↓

Kafka
```

Future platform components may also publish events.

Examples include:

- Data Quality notifications
- Processing completion events
- Monitoring events

---

## Consumers

Different consumers can independently process the same Kafka events.

Examples include:

```text
Kafka

├── Batch Processing

├── Streaming Processing

├── Monitoring

└── Future Applications
```

Consumers remain completely decoupled.

Adding a new consumer never impacts existing consumers.

---

# Workflow Orchestration Layer

## Apache Airflow

Apache Airflow is responsible for orchestrating the analytical platform.

It coordinates execution across multiple services while remaining independent from business logic.

Airflow never transforms data.

Instead, it controls when and how processing occurs.

---

## Responsibilities

Airflow is responsible for:

- Scheduling
- Dependency management
- Retry policies
- SLA monitoring
- Workflow execution
- Failure handling
- Branching
- Notifications
- Triggering Databricks Jobs

Airflow coordinates the platform but never processes datasets directly.

---

## What Airflow Does Not Do

Airflow does not:

- Read Kafka topics
- Execute SQL transformations
- Process Spark jobs
- Apply business rules
- Validate datasets
- Store analytical data

Those responsibilities belong to other platform components.

---

## DAG Organization

The platform organizes DAGs according to their responsibilities.

```text
dags/

foundation/

platform/

bronze/

silver/

gold/

analytics/

maintenance/
```

Each folder groups workflows serving a common purpose.

---

## Batch Execution

The default execution model uses scheduled batch processing.

The workflow follows the sequence below.

```text
Kafka

        │

        ▼

Airflow Scheduler

        │

        ▼

Databricks Job

        │

        ▼

Delta Lake

Bronze

↓

Silver

↓

Gold
```

Each execution processes only the required datasets.

Incremental processing is preferred whenever possible.

---

## Streaming Execution

The platform also supports near real-time processing.

In this mode, Databricks Structured Streaming continuously consumes Kafka topics.

```text
Kafka

        │

        ▼

Databricks Structured Streaming

        │

        ▼

Delta Lake

Bronze

↓

Silver

↓

Gold
```

Both Batch and Streaming pipelines share the same transformation logic whenever possible.

---

## Why Airflow

Airflow was selected because it provides:

- Mature orchestration
- Rich scheduling capabilities
- Retry mechanisms
- Dependency management
- Integration with Databricks
- Monitoring
- Extensibility

Its role is orchestration rather than data processing.

The following section describes how Amazon S3, Delta Lake and Databricks implement the platform's Lakehouse architecture.

# Data Lake

## Overview

The Data Lake is the foundation of the analytical platform.

Its primary responsibility is to provide durable, scalable and low-cost storage for every dataset generated throughout the analytical lifecycle.

The Data Lake stores data independently from processing engines, allowing multiple analytical technologies to consume the same datasets.

Within this platform, Amazon S3 is used as the Data Lake.

---

## Amazon S3

Amazon S3 provides highly durable object storage.

The platform uses S3 as the central repository for every processing layer.

S3 is responsible only for storage.

It never performs:

- Transformations
- Aggregations
- Business Rules
- SQL Queries

Those responsibilities belong to other platform components.

---

## Data Lake Structure

The Data Lake is organized according to the Medallion Architecture.

```text
s3://modern-data-platform/

bronze/

silver/

gold/

checkpoints/

logs/
```

Each directory represents a different processing stage.

---

## Benefits

Using Amazon S3 as the Data Lake provides several advantages.

- Virtually unlimited storage
- Low storage cost
- High durability
- Cloud-native architecture
- Separation between storage and compute
- Integration with multiple analytical engines

The storage layer remains independent from the processing engine.

---

# Delta Lake

## Overview

Delta Lake is the storage layer that transforms a traditional Data Lake into a transactional Lakehouse.

Instead of storing plain Parquet files, every analytical dataset is stored as a Delta Table.

This provides transactional guarantees while maintaining the scalability of object storage.

---

## Why Delta Lake

Traditional Data Lakes have several limitations.

Examples include:

- No ACID transactions
- No version control
- Difficult incremental processing
- Schema inconsistencies
- Complex MERGE operations

Delta Lake solves these limitations.

---

## Delta Tables

Every analytical dataset is stored as a Delta Table.

Example:

```text
bronze/

customers/

_delta_log/

part-0000.parquet

part-0001.parquet
```

The `_delta_log` directory stores the transaction history of the table.

Without it, the dataset would simply be a collection of Parquet files.

---

## Delta Features

Delta Lake provides enterprise capabilities including:

- ACID Transactions
- Schema Enforcement
- Schema Evolution
- Time Travel
- MERGE INTO
- UPDATE
- DELETE
- Incremental Processing
- Versioning
- Optimistic Concurrency Control

These capabilities enable reliable analytical processing over cloud object storage.

---

## Time Travel

Delta Lake maintains historical versions of every table.

This allows querying previous versions of the dataset.

Typical use cases include:

- Data recovery
- Pipeline debugging
- Auditing
- Historical analysis

---

## Incremental Processing

Instead of rewriting entire datasets, Delta Lake allows processing only new or modified records.

This significantly reduces processing time and cloud costs.

---

# Lakehouse Architecture

## Overview

The platform adopts the Lakehouse architecture.

A Lakehouse combines the scalability of a Data Lake with the reliability traditionally found in Data Warehouses.

Within this project, the Lakehouse consists of three independent technologies.

```text
Amazon S3

+

Delta Lake

+

Databricks

=

Lakehouse
```

Each component has a distinct responsibility.

---

## Amazon S3

Provides durable object storage.

---

## Delta Lake

Provides transactional capabilities over S3.

---

## Databricks

Provides distributed processing.

---

Together, these three technologies form the analytical platform.

---

# Distributed Processing

## Databricks

Databricks is the distributed processing engine of the platform.

Every transformation is implemented using Apache Spark through PySpark.

Databricks is responsible for converting raw transactional events into analytical datasets.

---

## Responsibilities

Databricks performs:

- Reading Delta Tables
- Writing Delta Tables
- Incremental Processing
- Business Transformations
- Data Cleaning
- Deduplication
- Data Standardization
- Aggregations
- Partitioning
- Performance Optimization

No orchestration logic exists inside Databricks.

That responsibility belongs to Airflow.

---

## Cluster Execution

Processing executes on Databricks clusters.

The platform supports:

- Interactive Clusters
- Job Clusters

Interactive clusters are primarily used during development.

Job clusters are created on demand by Airflow for production workloads.

---

## Workflows

Databricks Workflows organize Spark jobs into logical execution units.

Airflow triggers Workflows.

Databricks executes Spark.

This separation keeps orchestration independent from processing.

---

## PySpark

Every transformation is implemented using PySpark.

PySpark enables distributed execution across multiple workers while maintaining a simple programming model.

Typical operations include:

- Filtering
- Joins
- Window Functions
- Aggregations
- Deduplication
- Incremental MERGE operations

---

# Medallion Architecture

## Overview

The platform follows the Medallion Architecture.

Each processing layer increases data quality while reducing data complexity.

The three layers are:

- Bronze
- Silver
- Gold

---

# Bronze Layer

The Bronze Layer stores raw operational data.

Characteristics include:

- Immutable
- Append-only
- Historical preservation
- Original schema
- No business rules

Bronze represents the first landing zone inside the Lakehouse.

---

## Bronze Responsibilities

The Bronze Layer is responsible for:

- Preserving raw events
- Supporting reprocessing
- Maintaining historical data
- Acting as the recovery point

No analytical transformations occur in Bronze.

---

# Silver Layer

The Silver Layer contains standardized business data.

Raw operational records become reliable business entities.

Typical transformations include:

- Deduplication
- Type Conversion
- Null Handling
- Business Validation
- Schema Normalization
- Incremental MERGE

Silver becomes the trusted operational dataset.

---

## Silver Responsibilities

The Silver Layer guarantees:

- Clean records
- Standardized schema
- Business consistency
- Reliable joins

Most business rules are implemented here.

---

# Gold Layer

The Gold Layer contains business-ready analytical datasets.

This layer represents the Enterprise Data Warehouse.

Instead of storing operational entities, Gold stores analytical models.

Examples include:

- Fact Tables
- Dimension Tables
- KPIs
- Aggregations
- Business Metrics

Only curated datasets reach the Gold Layer.

---

## Gold Responsibilities

The Gold Layer is responsible for:

- Enterprise reporting
- Executive dashboards
- Business KPIs
- Analytical datasets
- Data marts

No raw operational data exists within Gold.

---

# Enterprise Data Warehouse

Although the platform stores data inside a Lakehouse, the Gold Layer logically represents the Enterprise Data Warehouse.

It contains dimensional models designed for analytical workloads.

Typical models include:

```text
Fact Orders

Dimension Customer

Dimension Product

Dimension Seller

Dimension Warehouse

Dimension Date
```

The Gold Layer becomes the single source of truth for business analytics.

The following section introduces the Semantic Layer, Data Governance and analytical consumption.

# Semantic Layer

## Overview

The Semantic Layer provides a business-oriented abstraction over the Enterprise Data Warehouse.

Instead of exposing raw analytical tables directly to consumers, the Semantic Layer organizes data into reusable business models that are easier to understand, maintain and consume.

The Semantic Layer is implemented using dbt Core.

---

## Why dbt

Databricks is responsible for distributed data processing.

dbt is responsible for analytical modeling.

Although both tools transform data, they solve different problems.

Databricks focuses on:

- Large-scale distributed processing
- Data ingestion
- Data cleansing
- Business transformations
- Incremental processing
- Performance optimization

dbt focuses on:

- Analytical modeling
- Star Schema
- Data Marts
- Documentation
- Data Lineage
- Data Testing
- Business Metrics

Together they provide a complete analytical architecture.

---

## Responsibilities

dbt is responsible for:

- Building Fact Tables
- Building Dimension Tables
- Creating Data Marts
- Defining Business Metrics
- Data Documentation
- Data Testing
- Data Lineage
- Dependency Management

dbt never performs ingestion.

dbt never orchestrates workflows.

dbt consumes curated datasets generated by the Lakehouse.

---

## Star Schema

The platform follows dimensional modeling.

Typical analytical models include:

```text
Dimensions

dim_customer

dim_product

dim_seller

dim_warehouse

dim_date

↓

Facts

fact_orders

fact_payments

fact_shipments

fact_inventory_movements
```

This model optimizes analytical workloads and simplifies dashboard development.

---

## Documentation

dbt automatically generates documentation describing:

- Models
- Columns
- Dependencies
- Lineage
- Business definitions

This documentation becomes part of the analytical platform.

---

## Data Testing

dbt validates analytical models before publication.

Examples include:

- Primary Keys
- Foreign Keys
- Not Null
- Unique Values
- Accepted Values
- Relationships

Analytical datasets are validated before reaching consumers.

---

# Data Governance

## Overview

Data Governance guarantees that published datasets are trustworthy, discoverable and compliant with business rules.

The platform implements governance using AWS Glue.

---

# AWS Glue Data Quality

AWS Glue Data Quality validates analytical datasets before publication.

Only datasets that satisfy predefined quality rules become available for analytical consumption.

Typical validation rules include:

- Not Null
- Unique
- Completeness
- Freshness
- Accepted Values
- Numeric Ranges
- Referential Consistency

Examples:

```text
customer_id IS NOT NULL

amount > 0

status IN

PAID

PENDING

CANCELLED
```

These validations ensure the Gold Layer contains reliable business information.

---

## Responsibilities

Glue Data Quality is responsible for:

- Dataset validation
- Quality reports
- Business rule verification
- Publication approval

It never transforms data.

---

# AWS Glue Data Catalog

The Glue Data Catalog provides centralized metadata management.

Rather than storing data itself, it stores metadata describing analytical datasets.

Examples include:

- Table names
- Column definitions
- Data types
- Locations
- Partitions

This enables AWS analytical services to discover available datasets.

---

## Catalog Structure

Example:

```text
Database

analytics

↓

Tables

fact_orders

fact_payments

dim_customer

dim_product

dim_date
```

Each table references Delta datasets stored in Amazon S3.

---

## Responsibilities

Glue Data Catalog is responsible for:

- Metadata
- Schema management
- Dataset discovery
- Athena integration

It never stores business data.

---

# Analytics Layer

## Amazon Athena

Amazon Athena provides serverless SQL access over analytical datasets.

Athena queries datasets directly from Amazon S3 using metadata provided by the Glue Data Catalog.

No data is copied into Athena.

Athena performs only analytical queries.

---

## Responsibilities

Athena is responsible for:

- Interactive SQL
- Ad-hoc analysis
- Business queries
- Dashboard connectivity

Athena never performs:

- ETL
- Data Processing
- Workflow Orchestration

---

## Typical Queries

Examples include:

- Sales by Month
- Top Customers
- Top Products
- Revenue by Seller
- Inventory Analysis
- Delivery Performance

Athena becomes the analytical entry point for business users.

---

# Visualization Layer

## Power BI

Power BI is the presentation layer of the platform.

Dashboards consume curated datasets exposed by Amazon Athena.

Power BI never connects directly to:

- PostgreSQL
- Kafka
- Bronze
- Silver

Only validated analytical datasets are exposed to dashboard consumers.

---

## Responsibilities

Power BI is responsible for:

- Dashboards
- Reports
- KPIs
- Executive Analytics
- Self-Service Analytics

Business users interact only with Power BI.

---

# Observability

## Amazon CloudWatch

CloudWatch provides centralized monitoring across the platform.

Observability is implemented as a cross-cutting concern rather than a processing layer.

CloudWatch collects:

- Logs
- Metrics
- Dashboards
- Alarms
- Events

---

## Monitored Components

CloudWatch monitors:

- Airflow
- AWS Infrastructure
- Glue
- Athena
- S3
- Platform Services

Future integrations may include:

- Lambda
- SNS
- EventBridge

---

## Monitoring Goals

CloudWatch enables:

- Failure detection
- Pipeline monitoring
- Infrastructure visibility
- Operational dashboards
- Alerting

Monitoring is separated from business processing.

---

# Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| Transaction Simulator | Generates realistic marketplace transactions |
| PostgreSQL | Transactional OLTP database |
| Debezium | Change Data Capture (CDC) |
| Apache Kafka | Event Streaming Platform |
| Apache Airflow | Workflow orchestration |
| Amazon S3 | Data Lake storage |
| Databricks | Distributed processing using PySpark |
| Delta Lake | Transactional storage layer |
| Gold Layer | Enterprise Data Warehouse |
| dbt Core | Semantic Layer |
| AWS Glue Data Quality | Data Quality validation |
| AWS Glue Data Catalog | Metadata catalog |
| Amazon Athena | Serverless SQL analytics |
| Amazon CloudWatch | Observability |
| Power BI | Business Intelligence |

Each technology performs only the responsibilities for which it was designed.

---

# Complete Platform Flow

```text
Transaction Simulator

↓

PostgreSQL

↓

Debezium

↓

Kafka

↓

Airflow

↓

Amazon S3 (Data Lake)

↓

Databricks (PySpark)

↓

Delta Lake

↓

Bronze

↓

Silver

↓

Gold (Enterprise Data Warehouse)

↓

dbt Core (Semantic Layer)

↓

Glue Data Quality

↓

Glue Data Catalog

↓

Athena

↓

Power BI
```

CloudWatch continuously monitors the entire platform.

---

# Design Principles

The platform follows modern architectural principles.

- Event-Driven Architecture
- Cloud-Native Architecture
- Cloud-Agnostic Design
- Infrastructure as Code
- Lakehouse Architecture
- Medallion Architecture
- Enterprise Data Warehouse
- Semantic Layer
- Separation of Responsibilities
- Incremental Processing
- ACID Storage
- Data Governance
- Data Quality
- Observability
- Scalability

---

# Current Implementation Status

| Component | Status |
|-----------|--------|
| Transaction Simulator | ✅ Completed |
| PostgreSQL | ✅ Completed |
| Debezium CDC | ✅ Completed |
| Apache Kafka | ✅ Completed |
| Apache Airflow | ✅ Completed |
| Terraform | 🚧 Planned |
| Amazon S3 (Data Lake) | 🚧 Planned |
| Databricks | 🚧 Planned |
| Delta Lake | 🚧 Planned |
| Bronze Layer | 🚧 Planned |
| Silver Layer | 🚧 Planned |
| Gold Layer (Enterprise Data Warehouse) | 🚧 Planned |
| dbt Core (Semantic Layer) | 🚧 Planned |
| AWS Glue Data Quality | 🚧 Planned |
| AWS Glue Data Catalog | 🚧 Planned |
| Amazon Athena | 🚧 Planned |
| Amazon CloudWatch | 🚧 Planned |
| Power BI | 🚧 Planned |

---

# Conclusion

Modern Data Platform demonstrates how modern cloud-native analytical platforms are built using best practices adopted by enterprise organizations.

The architecture combines Event Streaming, Workflow Orchestration, Lakehouse Architecture, Enterprise Data Warehousing, Semantic Modeling, Data Governance and Business Intelligence into a single end-to-end analytical platform.

Each technology is responsible only for the tasks it was designed to perform, resulting in a scalable, maintainable and cloud-agnostic architecture capable of supporting both batch and near real-time analytical workloads.