from datetime import datetime, timezone

from app.config import get_settings
from app.core.logging_config import log_event
from typing import Optional

_metric_events: list[dict[str, object]] = []


def record_metric(
    metric_name: str,
    value: float = 1.0,
    unit: str = "Count",
    dimensions: Optional[dict[str, str]] = None,
) -> None:
    settings = get_settings()
    if not settings.metrics_enabled:
        return

    event = {
        "namespace": settings.metrics_namespace,
        "metric_name": metric_name,
        "value": value,
        "unit": unit,
        "dimensions": dimensions or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _metric_events.append(event)
    log_event(
        "metric_recorded",
        event="metric_recorded",
        metric_name=metric_name,
        metric_value=value,
    )


def list_metric_events() -> list[dict[str, object]]:
    return list(_metric_events)