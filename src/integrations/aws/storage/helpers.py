from __future__ import annotations


def normalize_key(key: str) -> str:
    """
    Normalize an object key.

    Removes duplicate slashes and leading slash.
    """

    return "/".join(part for part in key.strip("/").split("/") if part)


def join_key(*parts: str) -> str:
    """
    Join multiple key parts into a normalized S3 key.
    """

    return normalize_key("/".join(parts))
