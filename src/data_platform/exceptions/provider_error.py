from data_platform.exceptions.platform_exception import PlatformException


class ProviderError(PlatformException):
    """
    Base exception for provider-related errors.
    """

    pass


class ProviderNotFoundError(ProviderError):
    """
    Raised when a provider is not registered.
    """

    pass


class ProviderAlreadyRegisteredError(ProviderError):
    """
    Raised when attempting to register an already registered provider.
    """

    pass


class InvalidProviderError(ProviderError):
    """
    Raised when a provider implementation is invalid.
    """

    pass
