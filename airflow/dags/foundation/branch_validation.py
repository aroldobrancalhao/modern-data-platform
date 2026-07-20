from datetime import datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator
from airflow.utils.trigger_rule import TriggerRule


def choose_branch():

    return "success"


with DAG(
    dag_id="branch_validation",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["foundation", "branch"],
) as dag:

    start = EmptyOperator(
        task_id="start",
    )

    branch = BranchPythonOperator(
        task_id="branch",
        python_callable=choose_branch,
    )

    success = EmptyOperator(
        task_id="success",
    )

    skipped = EmptyOperator(
        task_id="skipped",
    )

    finish = EmptyOperator(
        task_id="finish",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    start >> branch
    branch >> success >> finish
    branch >> skipped >> finish