import contextvars
import json
import logging
from datetime import datetime, timezone


request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id",
    default="-",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", request_id_context.get()),
        }

        optional_fields = (
            "document_id",
            "user_id",
            "event",
            "path",
            "method",
            "status_code",
            "duration_ms",
            "content_type",
            "source",
            "retry_count",
            "max_retry_count",
            "metric_name",
            "metric_value",
        )
        for field in optional_fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("app")
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger


def set_request_id(request_id: str) -> None:
    request_id_context.set(request_id)


def get_request_id() -> str:
    return request_id_context.get()


def clear_request_id() -> None:
    request_id_context.set("-")


def log_event(message: str, **fields: object) -> None:
    logger = logging.getLogger("app")
    logger.info(message, extra=fields)
