from data_platform.providers.provider_registry import ProviderRegistry

from integrations.aws.catalog.builder import GlueCatalogBuilder
from integrations.aws.storage.builder import S3StorageBuilder


def register(
    registry: ProviderRegistry,
) -> None:

    registry.register(
        "aws.s3",
        S3StorageBuilder,
    )

    registry.register(
        "aws.glue",
        GlueCatalogBuilder,
    )