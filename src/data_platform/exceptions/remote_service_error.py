from __future__ import annotations

from .provider_error import ProviderError


class RemoteServiceError(ProviderError):
    """
    Base exception for failures while communicating with remote services.
    """


class AuthenticationError(RemoteServiceError):
    """Authentication with the remote service failed."""


class AuthorizationError(RemoteServiceError):
    """The caller is not authorized to perform the operation."""


class ResourceNotFoundError(RemoteServiceError):
    """The requested resource does not exist."""


class ValidationError(RemoteServiceError):
    """The remote service rejected the request as invalid."""


class ConflictError(RemoteServiceError):
    """The request conflicts with the current resource state."""


class RateLimitError(RemoteServiceError):
    """The remote service rate limit has been exceeded."""


class ServiceUnavailableError(RemoteServiceError):
    """The remote service is temporarily unavailable."""


class RemoteTimeoutError(RemoteServiceError):
    """Communication with the remote service timed out."""