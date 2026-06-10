"""Integración HTTP: 429 y persistencia en rate_limit_events."""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.core.config import clear_settings_cache, get_settings
from app.models.audit import RateLimitEvent
from app.models.user import User
from app.services.passwords import hash_password
from tests.postgres_url import ensure_test_database_url_env
from tests.test_auth_crypto import _FakeRedis
from tests.test_auth_integration import _alembic_config, _ensure_database_exists, _reset_public_schema


@pytest.fixture(scope="module")
def rate_limit_postgres_url() -> str:
    if not os.environ.get("TEST_DATABASE_URL", "").strip():
        pytest.skip("Define TEST_DATABASE_URL para pruebas de rate limit.")
    url = ensure_test_database_url_env()
    if url is None:
        pytest.skip(
            "Postgres no accesible desde el host (probado 127.0.0.1, localhost y gateway WSL). "
            "Desde la raíz: docker compose up -d postgres && source scripts/ensure-test-infra.sh"
        )
    try:
        _ensure_database_exists(url)
    except OperationalError as e:
        pytest.skip(f"No se pudo conectar a Postgres para crear la base de test: {e}")
    _reset_public_schema(url)
    cfg = _alembic_config(url)
    from alembic import command

    command.upgrade(cfg, "head")
    return url


@pytest.fixture
def rate_limit_client(
    rate_limit_postgres_url: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DATABASE_URL", rate_limit_postgres_url)
    monkeypatch.setenv("APP_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_AUDIT_ENABLED", "true")
    monkeypatch.setenv("AUTH_LOGIN_MAX_ATTEMPTS_PER_IP_PER_MINUTE", "2")
    monkeypatch.setenv("AUTH_LOGIN_MAX_ATTEMPTS_PER_EMAIL_PER_MINUTE", "2")
    monkeypatch.setenv("APP_RATE_LIMIT_PER_MINUTE", "1000")
    monkeypatch.setenv("INGEST_UPLOAD_MAX_PER_USER_PER_MINUTE", "1")
    clear_settings_cache()

    settings = get_settings()
    engine = create_engine(rate_limit_postgres_url)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    email = f"rl_{uuid.uuid4().hex[:10]}@example.com"
    password = "rate-limit-test-password-9"
    with SessionLocal() as db:
        u = User(
            email=email,
            password_hash=hash_password(password, pepper=settings.password_pepper),
            role="user",
            is_active=True,
        )
        db.add(u)
        db.commit()

    from app.main import app

    app.state.redis_client = _FakeRedis()
    with TestClient(app) as client:
        yield client, email, password, SessionLocal
    app.state.redis_client = None
    clear_settings_cache()
    engine.dispose()


def test_login_returns_429_and_records_event(
    rate_limit_client: tuple[TestClient, str, str, sessionmaker],
) -> None:
    client, email, password, SessionLocal = rate_limit_client
    payload = {"email": email, "password": password}
    for _ in range(2):
        r = client.post("/api/auth/login", json=payload)
        assert r.status_code == 200, r.text
    r3 = client.post("/api/auth/login", json=payload)
    assert r3.status_code == 429, r3.text
    assert r3.json()["code"] == "RATE_LIMITED"

    with SessionLocal() as db:
        rows = db.execute(
            select(RateLimitEvent).where(RateLimitEvent.endpoint == "/api/auth/login")
        ).scalars().all()
        assert len(rows) >= 1


def test_authenticated_api_returns_429(
    rate_limit_client: tuple[TestClient, str, str, sessionmaker],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_RATE_LIMIT_PER_MINUTE", "2")
    clear_settings_cache()
    client, email, password, _SessionLocal = rate_limit_client
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(2):
        h = client.get("/api/kbs", headers=headers)
        assert h.status_code == 200
    h3 = client.get("/api/kbs", headers=headers)
    assert h3.status_code == 429
    assert h3.json()["code"] == "RATE_LIMITED"


def test_ingest_upload_quota_http_429(
    rate_limit_client: tuple[TestClient, str, str, sessionmaker],
) -> None:
    client, email, password, SessionLocal = rate_limit_client
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    kb = client.post(
        "/api/kbs",
        headers=headers,
        json={"name": "RL KB", "description": "test"},
    )
    assert kb.status_code == 201, kb.text
    kb_id = kb.json()["id"]

    from tests.test_documents_integration import _minimal_pdf

    pdf_bytes = _minimal_pdf()
    files = {"file": ("a.pdf", pdf_bytes, "application/pdf")}
    r1 = client.post(
        f"/api/kbs/{kb_id}/documents/upload",
        headers=headers,
        files=files,
    )
    assert r1.status_code == 202, r1.text
    r2 = client.post(
        f"/api/kbs/{kb_id}/documents/upload",
        headers=headers,
        files=files,
    )
    assert r2.status_code == 429, r2.text
    assert r2.json()["code"] == "RATE_LIMITED"

    with SessionLocal() as db:
        n = db.execute(
            text(
                "SELECT COUNT(*) FROM rate_limit_events "
                "WHERE endpoint LIKE '%/documents/upload'"
            )
        ).scalar_one()
        assert int(n) >= 1
