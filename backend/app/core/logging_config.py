"""Logging estructurado (JSON), correlación y redacción de campos sensibles."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.log_context import get_chat_id, get_document_id, get_kb_id
from app.core.request_context import get_request_id

_SENSITIVE_KEY = re.compile(
    r"(password|passwd|secret|token|authorization|cookie|set-cookie|api[_-]?key)",
    re.IGNORECASE,
)

_STANDARD_RECORD_ATTRS = frozenset(
    logging.LogRecord(
        name="",
        level=0,
        pathname="",
        lineno=0,
        msg="",
        args=(),
        exc_info=None,
    ).__dict__.keys()
) | frozenset({"message", "asctime"})


class CorrelationFilter(logging.Filter):
    """Inyecta request_id y IDs de correlación en cada LogRecord."""

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self._service_name = service_name

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = getattr(record, "request_id", None) or get_request_id() or "-"
        record.document_id = getattr(record, "document_id", None) or get_document_id() or "-"
        record.chat_id = getattr(record, "chat_id", None) or get_chat_id() or "-"
        record.kb_id = getattr(record, "kb_id", None) or get_kb_id() or "-"
        record.service = getattr(record, "service", None) or self._service_name
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
            "service": getattr(record, "service", "-"),
        }

        for field in (
            "document_id",
            "chat_id",
            "kb_id",
            "event",
            "method",
            "path",
            "status",
            "duration_ms",
        ):
            value = getattr(record, field, None)
            if value is not None and value != "-":
                payload[field] = value

        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_ATTRS or key.startswith("_"):
                continue
            if key in payload or value is None or value == "-":
                continue
            if _SENSITIVE_KEY.search(key):
                payload[key] = "***"
            else:
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)
        return json.dumps(_redact_value(payload), default=str, ensure_ascii=False)


def _resolve_log_file_path(settings: Settings, *, service_name: str) -> Path | None:
    if not settings.log_file_enabled or not settings.log_file_dir.strip():
        return None
    base = Path(settings.log_file_dir.strip())
    if not base.is_absolute():
        base = Path.cwd() / base
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{service_name}.jsonl"


def configure_logging(settings: Settings, *, service_name: str | None = None) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    svc = (service_name or settings.log_service_name).strip() or "rag-backend"
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    formatter = JsonFormatter() if settings.log_json_enabled else logging.Formatter(
        "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.addFilter(CorrelationFilter(svc))
    stream_handler.addFilter(RedactAttributesFilter())
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    log_path = _resolve_log_file_path(settings, service_name=svc)
    if log_path is not None:
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=settings.log_file_max_bytes,
            backupCount=settings.log_file_backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.addFilter(CorrelationFilter(svc))
        file_handler.addFilter(RedactAttributesFilter())
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(level)
