from enum import StrEnum


class ExecutionSource(StrEnum):
    AIRFLOW = "airflow"
    KAFKA = "kafka"
    API = "api"
    CLI = "cli"
    TEST = "test"