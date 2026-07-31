from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class AwsSettings:
    """
    Configuration for AWS services.

    ``region=None`` (the default) means "let boto3 resolve it from its
    own credential/region chain" -- environment variables
    (``AWS_REGION``, ``AWS_DEFAULT_REGION``), then ``~/.aws/config``.
    Pass an explicit value here only when you need to *force* a region
    different from the one already configured in the environment
    (e.g. a test, or a machine whose default region is wrong for this
    workload).
    """

    region: str | None = None

    access_key_id: str | None = None

    secret_access_key: str | None = None

    session_token: str | None = None

    endpoint_url: str | None = None

    profile: str | None = None