"""Log de acceso HTTP estructurado (JSON) para Loki."""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings
from app.core.log_context import correlation_fields
from app.observability.metrics import normalize_endpoint

_access_logger = logging.getLogger("rag.access")


class StructuredAccessLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._settings = settings

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        if not self._settings.log_access_enabled:
            return await call_next(request)

        path = request.url.path
        if path == self._settings.prometheus_metrics_path:
            return await call_next(request)

        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            _access_logger.error(
                "http_access",
                extra={
                    "event": "http_access",
                    "method": request.method,
                    "path": normalize_endpoint(path),
                    "status": 500,
                    "duration_ms": round(elapsed_ms, 2),
                    **correlation_fields(),
                },
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        _access_logger.info(
            "http_access",
            extra={
                "event": "http_access",
                "method": request.method,
                "path": normalize_endpoint(path),
                "status": response.status_code,
                "duration_ms": round(elapsed_ms, 2),
                **correlation_fields(),
            },
        )
        return response
