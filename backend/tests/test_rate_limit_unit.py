"""Tests unitarios de rate limits de aplicación (sin Postgres)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.services.rate_limit import (
    check_ingest_upload_quota,
    check_user_api_rate_limit,
)
from tests.test_auth_crypto import _FakeRedis


def test_user_api_rate_limit_blocks() -> None:
    r = _FakeRedis()
    s = Settings(
        environment="test",
        app_rate_limit_enabled=True,
        app_rate_limit_per_minute=2,
    )
    check_user_api_rate_limit(r, settings=s, user_id="u1")
    check_user_api_rate_limit(r, settings=s, user_id="u1")
    with pytest.raises(HTTPException) as ei:
        check_user_api_rate_limit(r, settings=s, user_id="u1")
    assert ei.value.status_code == 429
    assert ei.value.detail["code"] == "RATE_LIMITED"


def test_ingest_upload_quota_user_and_kb() -> None:
    r = _FakeRedis()
    s = Settings(
        environment="test",
        ingest_upload_max_per_user_per_minute=1,
        ingest_upload_max_per_kb_per_minute=5,
    )
    check_ingest_upload_quota(r, settings=s, user_id="u1", kb_id="kb1")
    with pytest.raises(HTTPException) as ei:
        check_ingest_upload_quota(r, settings=s, user_id="u1", kb_id="kb2")
    assert ei.value.status_code == 429
    assert ei.value.detail["details"]["scope"] == "ingest_user"

    r2 = _FakeRedis()
    s2 = Settings(
        environment="test",
        ingest_upload_max_per_user_per_minute=10,
        ingest_upload_max_per_kb_per_minute=1,
    )
    check_ingest_upload_quota(r2, settings=s2, user_id="u1", kb_id="kb1")
    with pytest.raises(HTTPException) as ei2:
        check_ingest_upload_quota(r2, settings=s2, user_id="u2", kb_id="kb1")
    assert ei2.value.detail["details"]["scope"] == "ingest_kb"
