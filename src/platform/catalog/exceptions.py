from platform.exceptions.platform_exception import PlatformException


class CatalogError(PlatformException):
    """Base catalog exception."""


class DatabaseNotFoundError(CatalogError):
    """Database not found."""


class DatabaseAlreadyExistsError(CatalogError):
    """Database already exists."""


class TableNotFoundError(CatalogError):
    """Table not found."""


class TableAlreadyExistsError(CatalogError):
    """Table already exists."""
