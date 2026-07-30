from integrations.airflow.config import AirflowSettings
from integrations.airflow.workflow.airflow_builder import (
    AirflowWorkflowBuilder,
)
from integrations.airflow.workflow.airflow_workflow_provider import (
    AirflowWorkflowProvider,
)


class TestAirflowWorkflowBuilder:

    def test_should_build_airflow_workflow_provider(self):

        builder = AirflowWorkflowBuilder(
            AirflowSettings,
        )

        provider = builder.build()

        assert isinstance(
            provider,
            AirflowWorkflowProvider,
        )