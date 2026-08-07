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
        """
        The streaming Bronze Consumer's table (``bronze_consumer.py``,
        Kafka/Debezium CDC, append-only, all 16 marketplace entities).

        Not read by the batch flow (``ingest_sources.ipynb`` and
        downstream) as of this method's introduction -- see
        ``.bronze_batch()``. The two used to share this same path,
        which produced real duplicate/inconsistent rows in Silver for
        entities that receive updates (found investigating a
        ``dim_products`` uniqueness failure -- batch's ``overwrite``
        and streaming's continuous ``append`` raced on the same Delta
        table with no reconciliation between them). See
        docs/architecture/roadmap-next-steps.md.
        """
        return cls._uri("bronze", entity)

    @classmethod
    def bronze_batch(cls, entity: str) -> str:
        """
        The batch flow's own Bronze table (``ingest_sources.ipynb``,
        ``validate_bronze.ipynb``, ``optimize_bronze.ipynb``,
        ``transform_silver.ipynb`` -- the Databricks "Full Pipeline"
        Job, the 7 entities the dbt/Gold star schema depends on),
        separate from ``.bronze()`` (streaming). Both are
        ``mode="overwrite"`` per run, so this path only ever holds one
        logical snapshot at a time, sourced solely from the most
        recent ``PostgresExtractionStage`` extraction -- no
        interference from Kafka/Debezium's independent append stream.
        """
        return cls._uri("bronze_batch", entity)

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
