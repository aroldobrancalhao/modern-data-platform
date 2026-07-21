from platform.providers.provider_registry import ProviderRegistry

from providers.aws.catalog.aws_glue_builder import AwsGlueBuilder
from providers.aws.storage.aws_s3_builder import AwsS3Builder


def register(
    registry: ProviderRegistry,
) -> None:

    registry.register(
        "aws.s3",
        AwsS3Builder,
    )

    registry.register(
        "aws.glue",
        AwsGlueBuilder,
    )
