from __future__ import annotations

from data_platform.exceptions import PlatformException


class HttpError(PlatformException):
    """
    Base HTTP exception.
    """


class HttpRequestError(HttpError):
    """
    Raised when the request cannot be executed.
    """


class HttpResponseError(HttpError):
    """
    Raised when the remote service returns an error response.
    """

    def __init__(
        self,
        status_code: int,
        message: str,
    ) -> None:
        super().__init__(message)

        self.status_code = status_code