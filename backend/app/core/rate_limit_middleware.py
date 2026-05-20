"""Middleware de rate limit por usuario (JWT) en rutas autenticadas."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.services.jwt_tokens import decode_access_token
from app.services.rate_limit import check_user_api_rate_limit
from app.services.rate_limit_audit import record_rate_limit_event

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

_SKIP_PREFIXES = (
    "/api/health",
    "/api/auth/login",
    "/api/auth/refresh",
    "/docs",
    "/redoc",
    "/openapi.json",
)


def _should_skip(path: str) -> bool:
    if path in ("/", "/api/openapi.json"):
        return True
    return any(path.startswith(p) for p in _SKIP_PREFIXES)


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


def _user_id_from_bearer(request: Request) -> uuid.UUID | None:
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth[7:].strip()
    if not token:
        return None
    try:
        payload = decode_access_token(token, get_settings())
        return uuid.UUID(str(payload["sub"]))
    except Exception:
        return None


class UserRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        path = request.url.path
        if _should_skip(path):
            return await call_next(request)

        redis_client = getattr(request.app.state, "redis_client", None)
        settings = get_settings()
        if not settings.app_rate_limit_enabled:
            return await call_next(request)

        user_id = _user_id_from_bearer(request)
        if user_id is None:
            return await call_next(request)

        try:
            check_user_api_rate_limit(
                redis_client,
                settings=settings,
                user_id=str(user_id),
            )
        except HTTPException as exc:
            if exc.status_code == 429:
                if settings.rate_limit_audit_enabled:
                    factory: sessionmaker | None = getattr(
                        request.app.state,
                        "db_session_factory",
                        None,
                    )
                    if factory is not None:
                        session = factory()
                        try:
                            detail = exc.detail if isinstance(exc.detail, dict) else {}
                            reason = str(detail.get("message", "RATE_LIMITED"))
                            record_rate_limit_event(
                                session,
                                user_id=user_id,
                                ip_address=_client_ip(request),
                                endpoint=path,
                                method=request.method,
                                reason=reason,
                            )
                            session.commit()
                        except Exception:
                            session.rollback()
                            logger.exception("No se pudo registrar rate_limit_event")
                        finally:
                            session.close()
                return JSONResponse(
                    status_code=429,
                    content=exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail},
                )
            raise

        return await call_next(request)
