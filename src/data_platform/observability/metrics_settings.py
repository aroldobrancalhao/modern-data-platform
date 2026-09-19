"""
Modern Data Platform

Prometheus Pushgateway configuration.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MetricsSettings(BaseSettings):
    """
    Configuration for pushing Prometheus metrics (see
    data_platform.processing.metrics.prometheus_metrics_hook).

    ``pushgateway_url`` defaults to "http://pushgateway:9091" -- the
    Docker-network hostname every in-container caller (Airflow tasks,
    the processing framework's own DAG-embedded stages) already
    resolves correctly, with no docker-compose env var needed for
    them. A host-run one-off script (scripts/run_silver_catalog_
    registration_once.py, scripts/run_postgres_extraction_once.py)
    doesn't sit on that network, so `pushgateway` fails to resolve
    from there -- found live 2026-09-19, running
    run_silver_catalog_registration_once.py from the host. Same shape
    as the KAFKA_BOOTSTRAP_SERVER host-vs-container split
    (integrations/kafka/config/kafka_settings.py), just the other
    field: PrometheusHook.push()'s existing ``settings`` parameter
    already lets a caller override this without touching the shared
    default, so the actual fix lives at each host-run script's own
    call site (construct MetricsSettings(pushgateway_url=...) with a
    host-friendly fallback, pass it to .push()), not here.
    """

    pushgateway_url: str = Field(
        default="http://pushgateway:9091",
        validation_alias="PROMETHEUS_PUSHGATEWAY_URL",
    )

    model_config = SettingsConfigDict(
        extra="ignore",
        # validation_alias restricts __init__ to the alias name only
        # by default -- populate_by_name additionally allows the
        # field's own Python name (pushgateway_url=...), which a
        # host-run script's explicit override (see class docstring)
        # needs. Without this, MetricsSettings(pushgateway_url=...)
        # silently ignores the kwarg and falls back to the
        # container-network default instead -- confirmed live, not
        # assumed (same failure mode KafkaSettings' own comment
        # already documented for KAFKA_BOOTSTRAP_SERVER).
        populate_by_name=True,
    )
