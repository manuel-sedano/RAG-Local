"""Integración HTTP de auth contra Postgres (opcional: TEST_DATABASE_URL)."""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import clear_settings_cache, get_settings
from app.models.user import User
from app.services.passwords import hash_password

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _ensure_database_exists(url: str) -> None:
    u = make_url(url)
    dbname = u.database or ""
    if not dbname or dbname in ("postgres", "template0", "template1"):
        return
    if not re.fullmatch(r"[A-Za-z0-9_]+", dbname):
        msg = f"TEST_DATABASE_URL: nombre de base no seguro: {dbname!r}"
        raise ValueError(msg)
    admin = u.set(database="postgres")
    engine = create_engine(admin, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": dbname},
        ).first()
        if exists is None:
            conn.execute(text(f'CREATE DATABASE "{dbname}"'))
    engine.dispose()


def _reset_public_schema(url: str) -> None:
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    engine.dispose()


def _alembic_config(url: str) -> Config:
    os.environ["DATABASE_URL"] = url
    clear_settings_cache()
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture(scope="module")
def auth_postgres_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("Define TEST_DATABASE_URL para pruebas de integración de auth.")
    _ensure_database_exists(url)
    _reset_public_schema(url)
    cfg = _alembic_config(url)
    command.upgrade(cfg, "head")
    return url


@pytest.fixture
def auth_client(
    auth_postgres_url: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DATABASE_URL", auth_postgres_url)
    clear_settings_cache()
    settings = get_settings()
    engine = create_engine(auth_postgres_url)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    email = f"auth_{uuid.uuid4().hex[:10]}@example.com"
    password = "integration-test-password-9chars"
    with SessionLocal() as db:
        u = User(
            email=email,
            password_hash=hash_password(password, pepper=settings.password_pepper),
            role="user",
            is_active=True,
        )
        db.add(u)
        db.commit()
        uid = str(u.id)
    engine.dispose()

    from app.main import app

    with TestClient(app) as client:
        yield client, email, password, uid
    clear_settings_cache()


def test_login_refresh_logout(auth_client: tuple[TestClient, str, str, str]) -> None:
    client, email, password, _uid = auth_client
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["email"] == email

    r2 = client.post(
        "/api/auth/refresh",
        json={"refresh_token": data["refresh_token"]},
    )
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert d2["access_token"] != data["access_token"]

    r3 = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {d2['access_token']}"},
        json={"refresh_token": d2["refresh_token"], "all_devices": False},
    )
    assert r3.status_code == 204

    r4 = client.post(
        "/api/auth/refresh",
        json={"refresh_token": d2["refresh_token"]},
    )
    assert r4.status_code == 401
