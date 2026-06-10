"""Middleware HTTP que expone latencia y contadores para Prometheus."""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings
from app.observability.metrics import normalize_endpoint, observe_http_request


class PrometheusMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._settings = settings

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        if not self._settings.prometheus_enabled:
            return await call_next(request)

        path = request.url.path
        if path == self._settings.prometheus_metrics_path or path.rstrip("/") == "/metrics":
            return await call_next(request)

        method = request.method
        endpoint = normalize_endpoint(path)
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            elapsed = time.perf_counter() - start
            observe_http_request(
                method=method,
                endpoint=endpoint,
                status=500,
                duration_s=elapsed,
            )
            raise

        elapsed = time.perf_counter() - start
        observe_http_request(
            method=method,
            endpoint=endpoint,
            status=response.status_code,
            duration_s=elapsed,
        )
        return response
