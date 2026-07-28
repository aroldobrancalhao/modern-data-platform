from enum import StrEnum, unique


@unique
class MonitoringKeys(StrEnum):
    """Keys describing observability metadata."""

    TRACE_ID = "monitoring.trace_id"

    SPAN_ID = "monitoring.span_id"

    REQUEST_ID = "monitoring.request_id"

    METRIC_NAMESPACE = "monitoring.metric_namespace"