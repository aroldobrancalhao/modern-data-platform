from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

from botocore.config import Config

from integrations.aws.config import AwsSettings
from integrations.aws.storage.s3_client import S3Client


def build_settings() -> AwsSettings:
    return AwsSettings(
        region="us-east-1",
        profile="default",
        endpoint_url="http://localhost:4566",
        access_key_id="access-key",
        secret_access_key="secret-key",
        session_token="session-token",
    )


@patch("boto3.Session")
def test_create_returns_boto3_client(
    mock_session,
) -> None:

    boto_session = MagicMock()
    boto_client = MagicMock()

    mock_session.return_value = boto_session
    boto_session.client.return_value = boto_client

    client = S3Client(build_settings())

    assert client.create() is boto_client


@patch("boto3.Session")
def test_create_builds_boto3_session(
    mock_session,
) -> None:

    boto_session = MagicMock()

    mock_session.return_value = boto_session
    boto_session.client.return_value = MagicMock()

    S3Client(build_settings()).create()

    mock_session.assert_called_once_with(
        aws_access_key_id="access-key",
        aws_secret_access_key="secret-key",
        aws_session_token="session-token",
        region_name="us-east-1",
        profile_name="default",
    )


@patch("boto3.Session")
def test_create_builds_s3_client(
    mock_session,
) -> None:

    boto_session = MagicMock()

    mock_session.return_value = boto_session
    boto_session.client.return_value = MagicMock()

    S3Client(build_settings()).create()

    boto_session.client.assert_called_once()

    args, kwargs = boto_session.client.call_args

    assert args == ("s3",)

    assert kwargs["endpoint_url"] == "http://localhost:4566"

    assert isinstance(
        kwargs["config"],
        Config,
    )


@patch("boto3.Session")
def test_create_uses_standard_retry_configuration(
    mock_session,
) -> None:

    boto_session = MagicMock()

    mock_session.return_value = boto_session
    boto_session.client.return_value = MagicMock()

    S3Client(build_settings()).create()

    _, kwargs = boto_session.client.call_args

    config: Config = kwargs["config"]

    assert config.retries["mode"] == "standard"
    assert config.retries["max_attempts"] == 10