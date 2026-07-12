# Project Decisions

## Purpose

This document defines the architectural decisions, technology stack, coding standards and implementation roadmap for the Modern Data Platform.

Its purpose is to establish a single source of truth for the project.

Unless a critical technical issue is found, the decisions described here must not change during the project's implementation.

---

# Project Goal

Build a production-inspired Modern Data Platform capable of demonstrating the complete lifecycle of modern data engineering.

The platform should simulate how large companies process transactional data, ingest changes in real time, build analytical datasets and expose business metrics.

The project is intended to showcase practical Data Engineering skills rather than academic examples.

---

# Business Domain

The project simulates an Online Marketplace inspired by large e-commerce platforms.

Business domains include:

- Customers
- Sellers
- Products
- Categories
- Inventory
- Orders
- Payments
- Shipments
- Reviews

Future modules:

- Refunds
- Chargebacks
- Fraud Detection

---

# Architectural Principles

The project follows these principles:

- Cloud Agnostic
- Event Driven Architecture
- Lakehouse Architecture
- Medallion Architecture
- ELT
- Infrastructure as Code
- Data Quality First
- Observability First
- Modular Architecture
- Domain Oriented Design
- Production Inspired

---

# Technology Stack

## Programming Language

Python 3.12

---

## Database

PostgreSQL 17

---

## Change Data Capture

Debezium

---

## Streaming

Apache Kafka

---

## Workflow Orchestration

Apache Airflow

---

## Data Processing

Apache Spark

PySpark

---

## Lakehouse

Delta Lake

---

## Analytics Engineering

dbt Core

---

## Cloud

AWS

Services:

- S3
- Glue
- Athena
- IAM
- CloudWatch

The architecture must remain cloud agnostic.

---

## Business Intelligence

Power BI

---

## Infrastructure

Docker

Docker Compose

Terraform

---

## Monitoring

Grafana

Prometheus

---

## Data Quality

Great Expectations

dbt Tests

---

## Version Control

Git

GitHub

GitHub Actions

---

# Python Standards

Dependency manager:

uv

Database library:

psycopg 3

Configuration:

Pydantic Settings

Domain Models:

dataclasses

Fake data generation:

Faker

No ORM will be used.

SQL must be explicit.

---

# Repository Structure

The repository structure is frozen.

```text
modern-data-platform/

docs/

infrastructure/

src/

tests/

scripts/

datasets/

dashboards/

config/
```

---

# Source Structure

```text
src/

cloud/

common/

ingestion/

processing/

quality/

streaming/

simulator/
```

No new top-level modules should be introduced without a clear architectural reason.

---

# Simulator Structure

```text
simulator/

core/

domain/

scheduler.py

app.py
```

---

# Domain Structure

Each business domain follows exactly the same organization.

```text
customer/

model.py

generator.py

repository.py

service.py
```

Future domains:

- catalog
- inventory
- orders
- payments
- logistics

must follow the same pattern.

---

# Responsibilities

Generator

Creates fake business data.

Repository

Contains SQL only.

Service

Coordinates business operations.

Model

Represents business entities.

Database

Responsible only for database connections.

Settings

Responsible only for configuration.

---

# SQL Standards

No ORM.

Parameterized SQL only.

All SQL statements must be explicit.

Transactions must be handled in the repository layer.

---

# Naming Convention

Python

snake_case

Classes

PascalCase

Constants

UPPER_CASE

Database

snake_case

Primary Keys

*_id

Foreign Keys

<entity>_id

Indexes

idx_<table>_<column>

Unique Constraints

uq_<table>_<column>

Foreign Keys

fk_<child>_<parent>

---

# Logging

Structured logging using structlog.

No print statements outside development tests.

---

# Configuration

All configuration must come from environment variables.

The .env file is used only for local development.

---

# Branch Strategy

main

Production-ready code.

feature/<name>

New features.

---

# Commit Convention

feat

fix

refactor

docs

test

chore

Examples:

feat(simulator): implement customer generator

feat(kafka): add order topic

docs: update architecture

---

# Roadmap

Sprint 1

Database

Completed

Sprint 2

Marketplace Simulator

Sprint 3

Debezium

Sprint 4

Apache Kafka

Sprint 5

Apache Airflow

Sprint 6

AWS

Sprint 7

Bronze Layer

Sprint 8

Silver Layer

Sprint 9

Gold Layer

Sprint 10

dbt

Sprint 11

Athena

Sprint 12

Power BI

Sprint 13

Observability

Sprint 14

Infrastructure as Code

Sprint 15

Fraud Detection

---

# Out of Scope

The following technologies are intentionally excluded.

Snowflake

Azure Synapse

Google BigQuery

Kubernetes

Apache Flink

Machine Learning

These technologies may be added in future versions but are not part of version 1.

---

# Project Rule

Architecture decisions described in this document are considered frozen.

Implementation should focus on delivering functionality instead of continuously redesigning the project.