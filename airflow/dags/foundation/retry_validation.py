from datetime import datetime
from datetime import timedelta

from airflow.decorators import dag, task
from airflow.models import Variable


@dag(
    dag_id="retry_validation",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={
        "retries": 1,
        "retry_delay": timedelta(seconds=5),
    },
    tags=["foundation", "retry"],
)
def retry_validation():

    @task
    def retry_test():

        executed = Variable.get(
            "retry_validation",
            default_var="false",
        )

        if executed == "false":

            Variable.set(
                "retry_validation",
                "true",
            )

            raise RuntimeError("First execution failed intentionally.")

        print("Retry succeeded.")

        Variable.set(
            "retry_validation",
            "false",
        )

    retry_test()


retry_validation()