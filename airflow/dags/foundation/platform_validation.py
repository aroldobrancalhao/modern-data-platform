from datetime import datetime

from airflow.decorators import dag, task
from airflow.models import Variable


@dag(
    dag_id="platform_validation",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["foundation", "validation"],
)
def platform_validation():

    @task
    def execution_context() -> dict:

        execution = {
            "timestamp": datetime.utcnow().isoformat(),
        }

        print(f"Execution: {execution}")

        return execution

    @task
    def read_variable() -> str:

        environment = Variable.get(
            "environment",
            default_var="local",
        )

        print(f"Environment: {environment}")

        return environment

    @task
    def validate(
        execution: dict,
        environment: str,
    ) -> None:

        print(f"Execution: {execution}")
        print(f"Environment: {environment}")

        assert environment == "local"

    validate(
        execution_context(),
        read_variable(),
    )


platform_validation()