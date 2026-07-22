from __future__ import annotations

from botocore.exceptions import ClientError


class AwsStorageErrorMapper:
    """
    Maps AWS exceptions to storage exceptions.
    """

    @staticmethod
    def is_not_found(error: ClientError) -> bool:

        code = error.response["Error"]["Code"]

        return code in {
            "404",
            "NoSuchKey",
            "NotFound",
        }
