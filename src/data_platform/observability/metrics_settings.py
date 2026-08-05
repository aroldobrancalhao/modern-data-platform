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
    """

    pushgateway_url: str = Field(
        default="http://pushgateway:9091",
        validation_alias="PROMETHEUS_PUSHGATEWAY_URL",
    )

    model_config = SettingsConfigDict(
        extra="ignore",
    )
