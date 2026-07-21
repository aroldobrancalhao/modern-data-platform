from enum import StrEnum


class ProviderType(StrEnum):
    """
    Platform capabilities.
    """

    STORAGE = "storage"
    COMPUTE = "compute"
    MESSAGING = "messaging"
    CATALOG = "catalog"
    QUERY = "query"
    QUALITY = "quality"
    MONITORING = "monitoring"
    NOTIFICATION = "notification"
    SECRETS = "secrets"
    IDENTITY = "identity"
