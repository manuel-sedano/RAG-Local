"""Tests unitarios de hashing, JWT y rate limit (sin Postgres ni fakeredis)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi import HTTPException

from app.core.config import Settings, clear_settings_cache, get_settings
from app.services.jwt_tokens import create_access_token, decode_access_token
from app.services.login_rate_limit import check_login_rate_limits, check_refresh_rate_limit
from app.services.passwords import hash_password, verify_password


class _FakePipeline:
    """Soporta la secuencia incr → expire usada por `check_login_rate_limits`."""

    def __init__(self, client: _FakeRedis) -> None:
        self._c = client
        self._ops: list[tuple[Any, ...]] = []

    def incr(self, key: str, amount: int = 1) -> _FakePipeline:
        self._ops.append(("incr", key, amount))
        return self

    def expire(self, key: str, ttl: int) -> _FakePipeline:
        self._ops.append(("expire", key, ttl))
        return self

    def execute(self) -> list[Any]:
        out: list[Any] = []
        for op in self._ops:
            if op[0] == "incr":
                out.append(self._c.incr(op[1], op[2]))
            else:
                out.append(self._c.expire(op[1], op[2]))
        self._ops.clear()
        return out


class _FakeRedis:
    """Redis mínimo en memoria (compatible con tests de rate limit)."""

    def __init__(self) -> None:
        self._int_counts: dict[str, int] = {}

    def incr(self, key: str, amount: int = 1) -> int:
        self._int_counts[key] = self._int_counts.get(key, 0) + int(amount)
        return self._int_counts[key]

    def expire(self, key: str, _ttl: int) -> bool:
        _ = key, _ttl
        return True

    def pipeline(self) -> _FakePipeline:
        return _FakePipeline(self)

    def delete(self, *keys: str) -> int:
        n = 0
        for k in keys:
            if k in self._int_counts:
                del self._int_counts[k]
                n += 1
        return n

    def ttl(self, key: str) -> int:
        _ = key
        return -1

    def setex(self, key: str, seconds: int, value: str) -> bool:
        _ = key, seconds, value
        return True


def _test_settings(**kwargs: object) -> Settings:
    base = dict(
        environment="test",
        database_url="postgresql+psycopg://t:t@127.0.0.1:5432/t",
        auth_login_max_attempts_per_ip_per_minute=30,
        auth_login_max_attempts_per_email_per_minute=15,
    )
    base.update(kwargs)
    return Settings(**base)  # type: ignore[arg-type]


@pytest.fixture
def settings() -> Settings:
    clear_settings_cache()
    s = get_settings()
    yield s
    clear_settings_cache()


def test_password_roundtrip(settings: Settings) -> None:
    h = hash_password("hunter2", pepper=settings.password_pepper)
    assert verify_password("hunter2", h, pepper=settings.password_pepper)
    assert not verify_password("wrong", h, pepper=settings.password_pepper)


def test_jwt_roundtrip(settings: Settings) -> None:
    uid = uuid.uuid4()
    token, jti = create_access_token(
        settings=settings,
        user_id=uid,
        email="a@b.co",
        role="user",
    )
    payload = decode_access_token(token, settings)
    assert payload["sub"] == str(uid)
    assert payload["jti"] == jti
    assert payload["role"] == "user"


def test_rate_limit_ip_blocks() -> None:
    s = _test_settings(
        auth_login_max_attempts_per_ip_per_minute=2,
        auth_login_max_attempts_per_email_per_minute=50,
    )
    r = _FakeRedis()
    check_login_rate_limits(r, settings=s, ip="1.1.1.1", email_normalized="u@x.co")
    check_login_rate_limits(r, settings=s, ip="1.1.1.1", email_normalized="u@x.co")
    with pytest.raises(HTTPException) as ei:
        check_login_rate_limits(r, settings=s, ip="1.1.1.1", email_normalized="u@x.co")
    assert ei.value.status_code == 429


def test_refresh_rate_limit() -> None:
    s = _test_settings(auth_login_max_attempts_per_ip_per_minute=2)
    r = _FakeRedis()
    check_refresh_rate_limit(r, settings=s, ip="2.2.2.2")
    check_refresh_rate_limit(r, settings=s, ip="2.2.2.2")
    with pytest.raises(HTTPException) as ei:
        check_refresh_rate_limit(r, settings=s, ip="2.2.2.2")
    assert ei.value.status_code == 429
