from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AWSSettings(BaseModel):
    """AWS provider configuration."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    region: str = Field(default="us-east-1")

    profile: str | None = None

    endpoint_url: str | None = None

    access_key_id: str | None = None

    secret_access_key: str | None = None

    session_token: str | None = None
