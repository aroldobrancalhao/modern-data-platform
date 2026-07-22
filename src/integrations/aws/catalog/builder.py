from data_platform.providers.provider_builder import ProviderBuilder

from integrations.aws.catalog.glue_catalog_provider import GlueCatalogProvider
from integrations.aws.core.aws_context import AwsContext
from data_platform.providers.provider import Provider


class GlueCatalogBuilder(ProviderBuilder):
    """
    Builds an AWS Glue catalog provider.
    """

    def build(self) -> Provider:
        context = AwsContext()

        return GlueCatalogProvider(context)