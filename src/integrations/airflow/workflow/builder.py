from __future__ import annotations

from data_platform.http import HttpClient

from integrations.airflow.config import AirflowSettings
from integrations.airflow.core import (
    AirflowClient,
    AirflowContext,
)

from .airflow_workflow_provider import AirflowWorkflowProvider


class AirflowBuilder:
    """
    Builds an Airflow workflow provider.
    """

    @staticmethod
    def build(
        settings: AirflowSettings,
    ) -> AirflowWorkflowProvider:

        http = HttpClient(
            base_url=settings.base_url,
            timeout=settings.timeout,
            verify_ssl=settings.verify_ssl,
        )

        context = AirflowContext(
            settings=settings,
            http=http,
        )

        client = AirflowClient(
            context,
        )

        return AirflowWorkflowProvider(
            client,
        )