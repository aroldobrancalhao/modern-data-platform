from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PlatformSettings(BaseSettings):
    """
    Platform configuration.
    """

    storage_provider: str = Field(
        default="aws.s3",
        validation_alias="PLATFORM_STORAGE_PROVIDER",
    )

    catalog_provider: str = Field(
        default="aws.glue",
        validation_alias="PLATFORM_CATALOG_PROVIDER",
    )

    compute_provider: str = Field(
        default="databricks",
        validation_alias="PLATFORM_COMPUTE_PROVIDER",
    )

    workflow_provider: str = Field(
        default="airflow",
        validation_alias="PLATFORM_WORKFLOW_PROVIDER",
    )

    model_config = SettingsConfigDict(
        extra="ignore",
    )


class Settings(PlatformSettings):
    """
    Backward compatibility alias.
    """

    pass