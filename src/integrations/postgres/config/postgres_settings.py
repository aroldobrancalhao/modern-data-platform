from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseSettings):
    """
    Postgres connection configuration.

    Defaults match the local docker compose stack
    (``infrastructure/docker/docker-compose.yml``,
    ``postgres-marketplace``) as seen from the host: ``localhost:5432``,
    database ``marketplace``, user/password ``postgres``.
    """

    host: str = Field(
        default="localhost",
        validation_alias="POSTGRES_HOST",
    )

    port: int = Field(
        default=5432,
        validation_alias="POSTGRES_PORT",
    )

    database: str = Field(
        default="marketplace",
        validation_alias="POSTGRES_DATABASE",
    )

    user: str = Field(
        default="postgres",
        validation_alias="POSTGRES_USER",
    )

    password: str = Field(
        default="postgres",
        validation_alias="POSTGRES_PASSWORD",
    )

    model_config = SettingsConfigDict(
        extra="ignore",
    )
