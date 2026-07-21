from __future__ import annotations

import boto3

from botocore.client import BaseClient

from .config import AWSSettings


class AWSSession:
    """
    Centralized boto3 session.

    Every AWS provider shares this session.
    """

    def __init__(self, settings: AWSSettings):
        self._settings = settings

        self._session = boto3.Session(
            profile_name=settings.profile,
            region_name=settings.region,
            aws_access_key_id=settings.access_key_id,
            aws_secret_access_key=settings.secret_access_key,
            aws_session_token=settings.session_token,
        )

    @property
    def session(self):
        return self._session

    def client(self, service: str) -> BaseClient:
        return self._session.client(
            service,
            endpoint_url=self._settings.endpoint_url,
        )

    def resource(self, service: str):
        return self._session.resource(
            service,
            endpoint_url=self._settings.endpoint_url,
        )
