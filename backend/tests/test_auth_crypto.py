"""Tests unitarios de hashing, JWT y rate limit (sin Postgres)."""

from __future__ import annotations

import uuid

import fakeredis
import pytest
from fastapi import HTTPException

from app.core.config import Settings, clear_settings_cache, get_settings
from app.services.jwt_tokens import create_access_token, decode_access_token
from app.services.login_rate_limit import check_login_rate_limits, check_refresh_rate_limit
from app.services.passwords import hash_password, verify_password


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
    r = fakeredis.FakeRedis(decode_responses=True)
    check_login_rate_limits(r, settings=s, ip="1.1.1.1", email_normalized="u@x.co")
    check_login_rate_limits(r, settings=s, ip="1.1.1.1", email_normalized="u@x.co")
    with pytest.raises(HTTPException) as ei:
        check_login_rate_limits(r, settings=s, ip="1.1.1.1", email_normalized="u@x.co")
    assert ei.value.status_code == 429


def test_refresh_rate_limit() -> None:
    s = _test_settings(auth_login_max_attempts_per_ip_per_minute=2)
    r = fakeredis.FakeRedis(decode_responses=True)
    check_refresh_rate_limit(r, settings=s, ip="2.2.2.2")
    check_refresh_rate_limit(r, settings=s, ip="2.2.2.2")
    with pytest.raises(HTTPException) as ei:
        check_refresh_rate_limit(r, settings=s, ip="2.2.2.2")
    assert ei.value.status_code == 429
