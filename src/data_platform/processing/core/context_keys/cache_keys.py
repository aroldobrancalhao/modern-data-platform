from enum import StrEnum, unique


@unique
class CacheKeys(StrEnum):
    """Keys describing distributed cache state."""

    LOCK_ID = "cache.lock_id"

    LEASE_ID = "cache.lease_id"

    TTL = "cache.ttl"