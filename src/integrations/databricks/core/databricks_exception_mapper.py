from __future__ import annotations

from databricks.sdk.errors import DatabricksError
from databricks.sdk.errors.platform import (
    BadRequest,
    DeadlineExceeded,
    NotFound,
    PermissionDenied,
    ResourceConflict,
    TemporarilyUnavailable,
    TooManyRequests,
    Unauthenticated,
)

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


class DatabricksExceptionMapper:
    """
    Translates databricks-sdk exceptions into the platform's shared
    RemoteServiceError family.

    This keeps the execution runtime isolated from the Databricks SDK,
    the same way HttpExceptionMapper isolates it from the Airflow
    REST client, per ADR-010 ("the execution engine MUST never
    depend on a specific product").

    databricks-sdk already models its errors as a class hierarchy
    (see databricks.sdk.errors.platform), so translation here is a
    matter of isinstance checks rather than a status-code lookup.
    Subclasses such as ResourceDoesNotExist(NotFound) or
    InvalidParameterValue(BadRequest) are covered automatically by
    their parent's branch.
    """

    @staticmethod
    def translate(
        exception: DatabricksError,
    ) -> RemoteServiceError:

        if isinstance(exception, Unauthenticated):
            return AuthenticationError(str(exception))

        if isinstance(exception, PermissionDenied):
            return AuthorizationError(str(exception))

        if isinstance(exception, NotFound):
            return ResourceNotFoundError(str(exception))

        if isinstance(exception, ResourceConflict):
            return ConflictError(str(exception))

        if isinstance(exception, TooManyRequests):
            return RateLimitError(str(exception))

        if isinstance(exception, TemporarilyUnavailable):
            return ServiceUnavailableError(str(exception))

        if isinstance(exception, DeadlineExceeded):
            return RemoteTimeoutError(str(exception))

        if isinstance(exception, BadRequest):
            return ValidationError(str(exception))

        return RemoteServiceError(str(exception))