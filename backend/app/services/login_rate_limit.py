"""Rate limit de login por IP/email y bloqueo progresivo por usuario (Redis)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.core.config import Settings

if TYPE_CHECKING:
    from redis import Redis


def _minute_bucket() -> str:
    return datetime.now(UTC).strftime("%Y%m%d%H%M")


def _ip_key(ip: str, bucket: str) -> str:
    return f"auth:rl:ip:{ip}:{bucket}"


def _email_key(email: str, bucket: str) -> str:
    return f"auth:rl:email:{email}:{bucket}"


def _fails_key(user_id: str) -> str:
    return f"auth:pwd_fails:{user_id}"


def _lockout_key(user_id: str) -> str:
    return f"auth:lockout:{user_id}"


def check_login_rate_limits(
    redis_client: "Redis | None",
    *,
    settings: Settings,
    ip: str,
    email_normalized: str,
) -> None:
    """Lanza 429 si se superan límites por IP o email (ventana ~1 min)."""
    if redis_client is None:
        return
    bucket = _minute_bucket()
    ip_k = _ip_key(ip, bucket)
    em_k = _email_key(email_normalized, bucket)
    pipe = redis_client.pipeline()
    pipe.incr(ip_k, 1)
    pipe.expire(ip_k, 70)
    pipe.incr(em_k, 1)
    pipe.expire(em_k, 70)
    c_ip, _, c_email, _ = pipe.execute()
    if c_ip > settings.auth_login_max_attempts_per_ip_per_minute:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMITED",
                "message": "Demasiados intentos de inicio de sesión desde esta IP.",
                "details": {"window": "per_minute", "scope": "ip"},
            },
        )
    if c_email > settings.auth_login_max_attempts_per_email_per_minute:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMITED",
                "message": "Demasiados intentos de inicio de sesión para este correo.",
                "details": {"window": "per_minute", "scope": "email"},
            },
        )


def check_refresh_rate_limit(
    redis_client: "Redis | None",
    *,
    settings: Settings,
    ip: str,
) -> None:
    """Limita refrescos por IP (ventana ~1 min), misma cuota que login por IP."""
    if redis_client is None:
        return
    bucket = _minute_bucket()
    key = f"auth:rl:refresh:ip:{ip}:{bucket}"
    n = int(redis_client.incr(key, 1))
    if n == 1:
        redis_client.expire(key, 70)
    if n > settings.auth_login_max_attempts_per_ip_per_minute:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMITED",
                "message": "Demasiados intentos de renovación de token.",
                "details": {"window": "per_minute", "scope": "ip"},
            },
        )


def check_user_lockout(redis_client: "Redis | None", *, settings: Settings, user_id: str) -> None:
    if redis_client is None:
        return
    ttl = redis_client.ttl(_lockout_key(user_id))
    if ttl is not None and ttl > 0:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMITED",
                "message": "Cuenta temporalmente bloqueada por intentos fallidos.",
                "details": {"retry_after_seconds": ttl},
            },
        )


def record_failed_password_attempt(
    redis_client: "Redis | None",
    *,
    settings: Settings,
    user_id: str,
) -> None:
    if redis_client is None:
        return
    n = int(redis_client.incr(_fails_key(user_id), 1))
    redis_client.expire(_fails_key(user_id), settings.auth_lockout_max_seconds * 4)
    if n < settings.auth_failed_password_threshold:
        return
    k = max(0, (n - settings.auth_failed_password_threshold) // settings.auth_failed_password_threshold)
    seconds = min(
        settings.auth_lockout_max_seconds,
        int(settings.auth_lockout_base_seconds * (2**k)),
    )
    redis_client.setex(_lockout_key(user_id), seconds, "1")


def clear_password_fail_counters(redis_client: "Redis | None", *, user_id: str) -> None:
    if redis_client is None:
        return
    redis_client.delete(_fails_key(user_id), _lockout_key(user_id))
