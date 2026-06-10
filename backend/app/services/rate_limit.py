"""Rate limits de aplicación (Redis): usuario autenticado y cuotas de ingesta."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.core.config import Settings

if TYPE_CHECKING:
    from redis import Redis


def minute_bucket() -> str:
    return datetime.now(UTC).strftime("%Y%m%d%H%M")


def raise_rate_limited(
    *,
    message: str,
    scope: str,
    window: str = "per_minute",
    retry_after_seconds: int | None = None,
) -> None:
    details: dict[str, str | int] = {"window": window, "scope": scope}
    if retry_after_seconds is not None:
        details["retry_after_seconds"] = retry_after_seconds
    raise HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "code": "RATE_LIMITED",
            "message": message,
            "details": details,
        },
    )


def _incr_with_ttl(redis_client: Redis, key: str, *, ttl_seconds: int = 70) -> int:
    n = int(redis_client.incr(key, 1))
    if n == 1:
        redis_client.expire(key, ttl_seconds)
    return n


def check_user_api_rate_limit(
    redis_client: Redis | None,
    *,
    settings: Settings,
    user_id: str,
) -> None:
    """Límite global por usuario autenticado (ventana ~1 min)."""
    if not settings.app_rate_limit_enabled or redis_client is None:
        return
    key = f"api:rl:user:{user_id}:{minute_bucket()}"
    n = _incr_with_ttl(redis_client, key)
    if n > settings.app_rate_limit_per_minute:
        raise_rate_limited(
            message="Demasiadas peticiones. Espera un momento e inténtalo de nuevo.",
            scope="user",
        )


def check_ingest_upload_quota(
    redis_client: Redis | None,
    *,
    settings: Settings,
    user_id: str,
    kb_id: str,
) -> None:
    """Cuota de subidas por usuario y por KB (ventana ~1 min)."""
    if redis_client is None:
        return
    bucket = minute_bucket()
    user_key = f"ingest:rl:user:{user_id}:{bucket}"
    kb_key = f"ingest:rl:kb:{kb_id}:{bucket}"
    pipe = redis_client.pipeline()
    pipe.incr(user_key, 1)
    pipe.expire(user_key, 70)
    pipe.incr(kb_key, 1)
    pipe.expire(kb_key, 70)
    n_user, _, n_kb, _ = pipe.execute()
    if n_user > settings.ingest_upload_max_per_user_per_minute:
        raise_rate_limited(
            message="Has alcanzado el límite de subidas por minuto. Espera e inténtalo de nuevo.",
            scope="ingest_user",
        )
    if n_kb > settings.ingest_upload_max_per_kb_per_minute:
        raise_rate_limited(
            message="Esta base de conocimiento ha alcanzado el límite de subidas por minuto.",
            scope="ingest_kb",
        )
