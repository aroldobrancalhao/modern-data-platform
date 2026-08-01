"""
Modern Data Platform

Unit tests for the platform provider bootstrap.

This locks down the regression fixed in Fase 3 of the ADR-010
consolidation roadmap: the Airflow WorkflowProvider was not being
registered by ``bootstrap()``.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from data_platform.bootstrap import bootstrap


def test_bootstrap_registers_aws_s3_storage_provider() -> None:
    registry = bootstrap()

    assert registry.contains("aws.s3") is True


def test_bootstrap_registers_aws_glue_catalog_provider() -> None:
    registry = bootstrap()

    assert registry.contains("aws.glue") is True


def test_bootstrap_registers_databricks_compute_provider() -> None:
    registry = bootstrap()

    assert registry.contains("databricks") is True


def test_bootstrap_registers_airflow_workflow_provider() -> None:
    registry = bootstrap()

    assert registry.contains("airflow") is True


def test_bootstrap_registers_kafka_messaging_provider() -> None:
    registry = bootstrap()

    assert registry.contains("kafka") is True


def test_bootstrap_registers_exactly_the_five_expected_providers() -> None:
    registry = bootstrap()

    assert registry.providers() == (
        "airflow",
        "aws.glue",
        "aws.s3",
        "databricks",
        "kafka",
    )
