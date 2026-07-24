from dataclasses import dataclass

from data_platform.http import HttpClient

from ..config.airflow_settings import AirflowSettings


@dataclass(slots=True, frozen=True)
class AirflowContext:
    settings: AirflowSettings
    http: HttpClient