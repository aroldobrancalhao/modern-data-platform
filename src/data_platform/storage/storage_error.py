from data_platform.exceptions import PlatformException


class StorageError(PlatformException):
    """
    Base storage exception.
    """

    pass


class BucketNotFoundError(StorageError):
    """
    Bucket does not exist.
    """

    pass


class ObjectNotFoundError(StorageError):
    """
    Object does not exist.
    """

    pass


class ObjectAlreadyExistsError(StorageError):
    """
    Object already exists.
    """

    pass


class StorageConnectionError(StorageError):
    """
    Storage backend unavailable.
    """

    pass
