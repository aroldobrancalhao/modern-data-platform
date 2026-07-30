from __future__ import annotations

from data_platform.contracts.workflow_provider import WorkflowProvider
from data_platform.http import HttpClient
from data_platform.providers.provider_builder import ProviderBuilder

from integrations.airflow.config import AirflowSettings
from integrations.airflow.core import (
    AirflowClient,
    AirflowContext,
)

from .airflow_workflow_provider import AirflowWorkflowProvider


class AirflowWorkflowBuilder(
    ProviderBuilder[WorkflowProvider],
):
    """
    Builds an Airflow workflow provider.
    """

    def build(
        self,
    ) -> WorkflowProvider:

        settings = AirflowSettings()

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