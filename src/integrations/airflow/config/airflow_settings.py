from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AirflowSettings(BaseSettings):
    """
    Airflow provider configuration.
    """

    base_url: str = Field(
        default="http://localhost:8080",
        validation_alias="AIRFLOW_BASE_URL",
    )

    username: str = Field(
        default="airflow",
        validation_alias="AIRFLOW_USERNAME",
    )

    password: str = Field(
        default="airflow",
        validation_alias="AIRFLOW_PASSWORD",
    )

    timeout: int = Field(
        default=30,
        validation_alias="AIRFLOW_TIMEOUT",
    )

    verify_ssl: bool = Field(
        default=True,
        validation_alias="AIRFLOW_VERIFY_SSL",
    )

    model_config = SettingsConfigDict(
        extra="ignore",
    )