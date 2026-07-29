from __future__ import annotations

from data_platform.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    RateLimitError,
    RemoteServiceError,
    RemoteTimeoutError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    ValidationError,
)

from .http_error import (
    HttpRequestError,
    HttpResponseError,
)


class HttpExceptionMapper:

    @staticmethod
    def translate(
        exception: HttpRequestError | HttpResponseError,
    ) -> RemoteServiceError:

        if isinstance(exception, HttpRequestError):
            return RemoteTimeoutError(str(exception))

        match exception.status_code:

            case 400:
                return ValidationError(str(exception))

            case 401:
                return AuthenticationError(str(exception))

            case 403:
                return AuthorizationError(str(exception))

            case 404:
                return ResourceNotFoundError(str(exception))

            case 409:
                return ConflictError(str(exception))

            case 429:
                return RateLimitError(str(exception))

            case 503:
                return ServiceUnavailableError(str(exception))

            case _:
                return RemoteServiceError(str(exception))