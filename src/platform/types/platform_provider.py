from enum import StrEnum


class PlatformProvider(StrEnum):
    """
    Supported infrastructure providers.
    """

    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    LOCAL = "local"
