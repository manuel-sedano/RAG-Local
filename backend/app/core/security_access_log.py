"""Log de acceso de seguridad (línea fija) para Fail2ban y Loki."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

if TYPE_CHECKING:
    from app.core.config import Settings

_SECURITY_LOGGER = logging.getLogger("security.access")

_STATUS_CODES = frozenset({401, 403, 429})


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "-"


def configure_security_access_logging(settings: Settings) -> None:
    """Opcional: archivo dedicado además de stdout (montar volumen en Docker)."""
    path = settings.fail2ban_security_log_path.strip()
    if not path:
        return
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    _SECURITY_LOGGER.addHandler(handler)
    _SECURITY_LOGGER.setLevel(logging.WARNING)
    _SECURITY_LOGGER.propagate = True


class SecurityAccessLogMiddleware(BaseHTTPMiddleware):
    """Emite SECURITY_ACCESS en 401/403/429 bajo /api (auth, rate limit, forbidden)."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        response: Response = await call_next(request)
        path = request.url.path
        if response.status_code in _STATUS_CODES and path.startswith("/api"):
            ip = _client_ip(request)
            _SECURITY_LOGGER.warning(
                "SECURITY_ACCESS client_ip=%s method=%s path=%s status=%s",
                ip,
                request.method,
                path,
                response.status_code,
            )
        return response
