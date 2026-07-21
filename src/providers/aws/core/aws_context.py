from functools import cached_property

import boto3

from providers.aws.config import AwsSettings


class AwsContext:
    """
    Shared AWS context.

    Responsible for creating sessions,
    clients and resources.
    """

    def __init__(
        self,
        settings: AwsSettings | None = None,
    ) -> None:

        self._settings = settings or AwsSettings()

    @property
    def settings(self) -> AwsSettings:
        return self._settings

    @cached_property
    def session(self):
        return boto3.Session(
            region_name=self.settings.region,
            profile_name=self.settings.profile,
        )

    def client(
        self,
        service: str,
    ):

        kwargs = {}

        if self.settings.endpoint_url:
            kwargs["endpoint_url"] = self.settings.endpoint_url

        return self.session.client(
            service,
            **kwargs,
        )

    def resource(
        self,
        service: str,
    ):

        kwargs = {}

        if self.settings.endpoint_url:
            kwargs["endpoint_url"] = self.settings.endpoint_url

        return self.session.resource(
            service,
            **kwargs,
        )
