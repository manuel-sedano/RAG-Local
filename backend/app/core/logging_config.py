"""Logging estructurado (JSON), request_id y redacción básica de campos sensibles."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings
from app.core.request_context import get_request_id

_SENSITIVE_KEY = re.compile(
    r"(password|passwd|secret|token|authorization|cookie|set-cookie|api[_-]?key)",
    re.IGNORECASE,
)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


class RedactAttributesFilter(logging.Filter):
    """Evita que atributos del LogRecord con nombres sensibles se impriman en claro."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key, _value in list(record.__dict__.items()):
            if key.startswith("_") or key in {"msg", "args", "levelname", "levelno"}:
                continue
            if _SENSITIVE_KEY.search(key):
                setattr(record, key, "***")
        return True


def _redact_value(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: ("***" if _SENSITIVE_KEY.search(k) else _redact_value(v)) for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact_value(v) for v in obj]
    return obj


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)
        return json.dumps(_redact_value(payload), default=str, ensure_ascii=False)


def configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.addFilter(RequestIdFilter())
    handler.addFilter(RedactAttributesFilter())
    handler.setFormatter(JsonFormatter())

    root.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(level)
    logging.getLogger("uvicorn.error").setLevel(level)
