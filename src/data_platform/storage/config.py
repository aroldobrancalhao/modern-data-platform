from __future__ import annotations

from pydantic import BaseModel


class StorageSettings(BaseModel):
    """
    Common storage configuration.
    """

    provider: str = "local"

    default_bucket: str = "mdp-datalake-dev-857854758128"
    """
    The project's conventioned Data Lake bucket (provisioned by
    Terraform, ``sa-east-1``). This is an explicit, overridable
    default -- same pattern as ``DatabricksSettings.profile`` -- not a
    placeholder: every environment this platform runs against today
    uses this exact bucket.
    """

    create_bucket_if_missing: bool = True

    overwrite: bool = True


class StorageConfig:
    """
    Derives the canonical S3 URI for each Medallion layer from
    ``StorageSettings``.

    A thin, instantiation-free helper (``StorageConfig.bronze(...)``,
    not ``StorageConfig().bronze(...)``) -- mirrors how notebooks
    already expected to call it (see ``notebooks/bronze/*.ipynb``).
    Reads the bucket from ``StorageSettings()`` on every call rather
    than caching it, since these are cheap, stateless lookups with no
    call site that constructs a custom ``StorageSettings`` instance
    today.
    """

    @classmethod
    def raw(cls, entity: str) -> str:
        return cls._uri("raw", entity)

    @classmethod
    def bronze(cls, entity: str) -> str:
        return cls._uri("bronze", entity)

    @classmethod
    def silver(cls, entity: str) -> str:
        return cls._uri("silver", entity)

    @classmethod
    def gold(cls, entity: str) -> str:
        """
        No current caller as of ADR-011 (Databricks/Spark's
        responsibility now ends at Silver; ``publish_gold.ipynb`` and
        the Gold Job were removed). Kept, not dead code: when dbt
        materializes the Gold star schema via ``dbt-athena`` (ADR-011's
        next step), it will very likely write under this same
        ``gold/{entity}/`` S3 prefix -- this becomes the real path
        builder for that configuration, not decorative symmetry with
        ``.bronze()``/``.silver()``.
        """
        return cls._uri("gold", entity)

    @staticmethod
    def _uri(layer: str, entity: str) -> str:
        bucket = StorageSettings().default_bucket

        return f"s3://{bucket}/{layer}/{entity}"
