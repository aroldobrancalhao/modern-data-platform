from data_platform.exceptions.platform_exception import PlatformException


class CapabilityError(PlatformException):
    """
    Base exception for capability-related errors.
    """

    pass


class CapabilityNotSupportedError(CapabilityError):
    """
    Raised when a provider does not implement a requested capability.
    """

    pass
