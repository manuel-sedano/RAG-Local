"""Tests opcionales contra Redis real (rate limit + lockout).

No se ejecutan en CI por defecto. Para activarlos:

  export TEST_REDIS_URL='redis://127.0.0.1:6379/15'

Usa una base lógica dedicada (p. ej. `/15`) para no mezclar con datos locales.
Redis debe estar escuchando en esa URL (p. ej. `docker compose up -d redis` en la raíz;
el `docker-compose.yml` publica `127.0.0.1:6379`). Si no conecta, los tests se omiten (skip),
no fallan como error de fixture.
"""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.services.login_rate_limit import (
    _email_key,
    _fails_key,
    _ip_key,
    _lockout_key,
    _minute_bucket,
    check_login_rate_limits,
    check_refresh_rate_limit,
    check_user_lockout,
    clear_password_fail_counters,
    record_failed_password_attempt,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_REDIS_URL", "").strip(),
    reason="Define TEST_REDIS_URL (p. ej. redis://127.0.0.1:6379/15) para tests con Redis real.",
)


@pytest.fixture
def redis_real():
    import redis as redis_mod
    from redis.exceptions import ConnectionError as RedisConnectionError
    from redis.exceptions import TimeoutError as RedisTimeoutError

    url = os.environ["TEST_REDIS_URL"].strip()
    client = redis_mod.from_url(url, decode_responses=True, socket_connect_timeout=2.0)
    try:
        client.ping()
    except (RedisConnectionError, RedisTimeoutError, OSError) as exc:
        client.close()
        pytest.skip(
            f"Redis no alcanzable ({url}): {exc}. "
            "Levanta el servicio (p. ej. desde la raíz del repo: `docker compose up -d redis`)."
        )
    yield client
    client.close()


def _settings(**kwargs: object) -> Settings:
    base: dict[str, object] = {
        "environment": "test",
        "database_url": "postgresql+psycopg://t:t@127.0.0.1:5432/t",
        "auth_login_max_attempts_per_ip_per_minute": 30,
        "auth_login_max_attempts_per_email_per_minute": 15,
    }
    base.update(kwargs)
    return Settings(**base)  # type: ignore[arg-type]


def test_redis_login_rate_limit_by_ip(redis_real) -> None:
    suffix = uuid.uuid4().hex[:12]
    ip = f"pytest-ip-{suffix}"
    email = f"pytest-{suffix}@example.com"
    s = _settings(
        auth_login_max_attempts_per_ip_per_minute=2,
        auth_login_max_attempts_per_email_per_minute=50,
    )
    try:
        check_login_rate_limits(redis_real, settings=s, ip=ip, email_normalized=email)
        check_login_rate_limits(redis_real, settings=s, ip=ip, email_normalized=email)
        with pytest.raises(HTTPException) as ei:
            check_login_rate_limits(redis_real, settings=s, ip=ip, email_normalized=email)
        assert ei.value.status_code == 429
    finally:
        b = _minute_bucket()
        redis_real.delete(_ip_key(ip, b), _email_key(email, b))


def test_redis_login_rate_limit_by_email(redis_real) -> None:
    suffix = uuid.uuid4().hex[:12]
    email = f"pytest-em-{suffix}@example.com"
    s = _settings(
        auth_login_max_attempts_per_ip_per_minute=100,
        auth_login_max_attempts_per_email_per_minute=2,
    )
    ips = [f"10.0.{i}.1" for i in range(3)]
    try:
        check_login_rate_limits(redis_real, settings=s, ip=ips[0], email_normalized=email)
        check_login_rate_limits(redis_real, settings=s, ip=ips[1], email_normalized=email)
        with pytest.raises(HTTPException) as ei:
            check_login_rate_limits(redis_real, settings=s, ip=ips[2], email_normalized=email)
        assert ei.value.status_code == 429
        assert ei.value.detail["details"]["scope"] == "email"
    finally:
        b = _minute_bucket()
        redis_real.delete(_email_key(email, b), *[_ip_key(ip, b) for ip in ips])


def test_redis_refresh_rate_limit(redis_real) -> None:
    suffix = uuid.uuid4().hex[:12]
    ip = f"pytest-refresh-{suffix}"
    s = _settings(auth_login_max_attempts_per_ip_per_minute=2)
    b = _minute_bucket()
    key = f"auth:rl:refresh:ip:{ip}:{b}"
    try:
        check_refresh_rate_limit(redis_real, settings=s, ip=ip)
        check_refresh_rate_limit(redis_real, settings=s, ip=ip)
        with pytest.raises(HTTPException) as ei:
            check_refresh_rate_limit(redis_real, settings=s, ip=ip)
        assert ei.value.status_code == 429
    finally:
        redis_real.delete(key)


def test_redis_lockout_after_failed_attempts(redis_real) -> None:
    user_id = str(uuid.uuid4())
    s = _settings(
        auth_failed_password_threshold=3,
        auth_lockout_base_seconds=60,
        auth_lockout_max_seconds=3600,
    )
    try:
        record_failed_password_attempt(redis_real, settings=s, user_id=user_id)
        record_failed_password_attempt(redis_real, settings=s, user_id=user_id)
        check_user_lockout(redis_real, settings=s, user_id=user_id)
        record_failed_password_attempt(redis_real, settings=s, user_id=user_id)
        with pytest.raises(HTTPException) as ei:
            check_user_lockout(redis_real, settings=s, user_id=user_id)
        assert ei.value.status_code == 429
        ttl = redis_real.ttl(_lockout_key(user_id))
        assert ttl is not None and ttl > 0
        assert ttl <= 3600
    finally:
        clear_password_fail_counters(redis_real, user_id=user_id)
        redis_real.delete(_fails_key(user_id), _lockout_key(user_id))
