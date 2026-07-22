from data_platform.providers.provider_builder import ProviderBuilder

from integrations.aws.core.aws_context import AwsContext
from integrations.aws.storage.s3_storage_provider import S3StorageProvider
from data_platform.providers.provider import Provider


class S3StorageBuilder(ProviderBuilder):
    """
    Builds an AWS S3 storage provider.
    """

    def build(self) -> Provider:
        context = AwsContext()

        return S3StorageProvider(
            context.client("s3"),
        )