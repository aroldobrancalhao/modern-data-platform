from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class AwsSettings:
    """
    Configuration for AWS services.
    """

    region: str = "us-east-1"

    access_key_id: str | None = None

    secret_access_key: str | None = None

    session_token: str | None = None

    endpoint_url: str | None = None

    profile: str | None = None