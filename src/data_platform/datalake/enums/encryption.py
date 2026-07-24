from enum import StrEnum


class Encryption(StrEnum):
    """
    Supported encryption strategies for datasets.

    Initially the platform will use no encryption locally and may use
    AWS-managed encryption in cloud environments.
    """

    NONE = "none"
    SSE_S3 = "sse-s3"
    SSE_KMS = "sse-kms"