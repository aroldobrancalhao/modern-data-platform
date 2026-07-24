from __future__ import annotations

import pytest

from data_platform.http import HttpClient

from integrations.airflow.config import AirflowSettings
from integrations.airflow.core import (
    AirflowClient,
    AirflowContext,
)
from integrations.airflow.workflow import AirflowWorkflowProvider


@pytest.fixture(scope="session")
def airflow_settings() -> AirflowSettings:
    return AirflowSettings(
        base_url="http://localhost:8080",
        username="airflow",
        password="airflow",
        timeout=30,
        verify_ssl=True,
    )


@pytest.fixture(scope="session")
def http_client(
    airflow_settings: AirflowSettings,
) -> HttpClient:
    return HttpClient(
        base_url=airflow_settings.base_url,
        timeout=airflow_settings.timeout,
        verify_ssl=airflow_settings.verify_ssl,
    )


@pytest.fixture(scope="session")
def airflow_context(
    airflow_settings: AirflowSettings,
    http_client: HttpClient,
) -> AirflowContext:
    return AirflowContext(
        settings=airflow_settings,
        http=http_client,
    )


@pytest.fixture(scope="session")
def airflow_client(
    airflow_context: AirflowContext,
) -> AirflowClient:
    return AirflowClient(
        airflow_context,
    )


@pytest.fixture(scope="session")
def workflow_provider(
    airflow_client: AirflowClient,
) -> AirflowWorkflowProvider:
    return AirflowWorkflowProvider(
        airflow_client,
    )