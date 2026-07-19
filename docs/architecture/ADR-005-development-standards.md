# ADR-005: Development Standards

- **Status:** Accepted
- **Date:** 2026-07-19
- **Decision Makers:** Project Maintainers

---

# Context

A consistent engineering standard is essential for building maintainable, scalable, and collaborative software.

Without clear development standards, projects tend to accumulate technical debt, inconsistent coding styles, duplicated solutions, and poor maintainability.

This document establishes the engineering standards for the Modern Data Platform.

---

# Decision

All source code, infrastructure, documentation, and analytical assets must follow the standards defined in this document.

These standards apply to every contribution regardless of project size.

---

# Engineering Principles

Development should prioritize:

- Readability
- Maintainability
- Simplicity
- Testability
- Reproducibility
- Observability
- Consistency

Code is expected to be read more often than it is written.

---

# Programming Language

Primary language:

- Python 3.13+

Supporting languages:

- SQL
- Terraform
- YAML
- Bash

---

# Python Style

The project follows:

- PEP 8
- PEP 257
- PEP 484
- PEP 561

Formatting is automated.

Developers should never manually format code.

---

# Code Formatter

Formatter

```
Black
```

Line length

```
88 characters
```

Formatting is enforced automatically.

---

# Linting

Linter

```
Ruff
```

Responsibilities

- Code style
- Imports
- Complexity
- Best practices
- Dead code detection

---

# Static Typing

Type checking

```
MyPy
```

Requirements

- Public functions must be typed.
- Return types are mandatory.
- Optional values must use Optional[T].
- Avoid Any whenever possible.

Example

```python
def load_data(path: Path) -> DataFrame:
    ...
```

---

# Imports

Import order

1. Standard Library
2. Third-party packages
3. Internal packages

Example

```python
from pathlib import Path

import pandas as pd

from platform.storage import StorageProvider
```

Avoid wildcard imports.

Forbidden

```python
from module import *
```

---

# Naming Conventions

Packages

```
snake_case
```

Modules

```
snake_case
```

Classes

```
PascalCase
```

Functions

```
snake_case
```

Variables

```
snake_case
```

Constants

```
UPPER_SNAKE_CASE
```

Private methods

```
_prefix()
```

---

# Project Structure

Every new component must comply with ADR-004.

Components must never be created outside their designated module.

---

# Documentation

Every public module should contain:

- Purpose
- Responsibilities
- Examples when appropriate

Public APIs require docstrings.

Use Google Style Docstrings.

Example

```python
def publish(event: Event) -> None:
    """
    Publish an event.

    Args:
        event: Event to publish.

    Returns:
        None.
    """
```

---

# Logging

Use

```
logging
```

or

```
structlog
```

Guidelines

- Structured logs
- No print statements
- Log meaningful events
- Include contextual information

Example

```
pipeline_id

execution_id

dataset

duration
```

---

# Error Handling

Raise meaningful exceptions.

Preferred

```python
raise DatasetNotFoundError(dataset)
```

Avoid

```python
raise Exception()
```

Exceptions should be specific.

---

# Configuration

Configuration must never be hardcoded.

Use

- Environment Variables
- Pydantic Settings
- Secret Managers

Forbidden

```python
bucket = "production-data"
```

Preferred

```python
settings.storage.bucket
```

---

# Dependency Injection

Dependencies should be injected.

Preferred

```python
class BronzeProcessor:

    def __init__(
        self,
        storage: StorageProvider,
    ):
        ...
```

Avoid

```python
storage = S3Provider()
```

inside business logic.

---

# Data Processing

Processing should be:

- Idempotent
- Deterministic
- Incremental whenever possible

Avoid mutable global state.

---

# Spark Standards

Jobs should:

- Use DataFrame API
- Avoid unnecessary collect()
- Minimize shuffle operations
- Cache only when justified
- Prefer partition pruning

Business logic should remain independent from Spark configuration.

---

# Airflow Standards

DAGs should orchestrate.

DAGs should not implement business logic.

Preferred

```
Task

↓

Service

↓

Platform
```

Avoid

```
Task

↓

AWS SDK
```

Keep DAG files lightweight.

---

# dbt Standards

Models should follow the Medallion Architecture.

```
Bronze

↓

Silver

↓

Gold
```

Model names

```
stg_

int_

dim_

fact_
```

Snapshots should be used for historical tracking.

---

# Terraform Standards

Infrastructure should be modular.

Structure

```
modules/

providers/

environments/
```

Avoid duplicated resources.

Variables must be typed.

Outputs should be documented.

---

# Docker Standards

Containers should:

- Be reproducible
- Minimize image size
- Use multi-stage builds whenever appropriate
- Avoid running as root

---

# Testing Strategy

Required test levels

- Unit
- Integration
- Contract
- End-to-End

Critical business logic requires unit tests.

---

# Code Coverage

Recommended minimum

```
80%
```

Coverage should not replace meaningful testing.

---

# Git Workflow

Branch naming

```
feature/

bugfix/

hotfix/

docs/

refactor/
```

Examples

```
feature/platform-storage

feature/bronze-processing

docs/adr-005
```

---

# Commit Convention

Follow Conventional Commits.

Examples

```
feat:

fix:

docs:

refactor:

test:

ci:

build:
```

Example

```
feat(storage): implement S3 provider
```

---

# Pull Requests

Every Pull Request should include

- Description
- Motivation
- Testing evidence
- Related issue

Large Pull Requests should be avoided.

---

# CI/CD Requirements

Pipeline should validate

- Ruff
- Black
- MyPy
- Tests
- Terraform Format
- Terraform Validate
- dbt Tests

Future additions

- Security Scanning
- Dependency Scanning
- Container Scanning

---

# Security

Never commit

- Credentials
- Secrets
- Tokens
- Certificates

Sensitive data must use Secret Managers.

---

# Performance

Optimize only after measuring.

Prefer readable code over premature optimization.

---

# Documentation Standards

Every architectural decision should become an ADR.

README must remain synchronized with the implementation.

Diagrams should be updated whenever architecture changes.

---

# Technical Debt

Technical debt should be documented.

Temporary solutions require

- justification
- owner
- removal plan

---

# Definition of Done

A feature is considered complete only if

- Code is implemented
- Tests pass
- Documentation is updated
- Lint passes
- Formatting passes
- Type checking passes
- CI passes
- Architecture is respected

---

# Related ADRs

- ADR-000 – Architecture Principles
- ADR-001 – Platform Architecture
- ADR-002 – Platform Contracts
- ADR-003 – Cloud Strategy
- ADR-004 – Repository Structure