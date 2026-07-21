from __future__ import annotations

import boto3
from botocore.client import BaseClient
from botocore.config import Config

from providers.aws.config import AwsSettings


class S3Client:
    """
    Factory responsible for creating a configured boto3 S3 client.
    """

    def __init__(self, settings: AwsSettings):
        self._settings = settings

    def create(self) -> BaseClient:
        session = boto3.Session(
            aws_access_key_id=self._settings.access_key_id,
            aws_secret_access_key=self._settings.secret_access_key,
            aws_session_token=self._settings.session_token,
            region_name=self._settings.region,
            profile_name=self._settings.profile,
        )

        return session.client(
            "s3",
            endpoint_url=self._settings.endpoint_url,
            config=Config(
                retries={
                    "max_attempts": 10,
                    "mode": "standard",
                }
            ),
        )
