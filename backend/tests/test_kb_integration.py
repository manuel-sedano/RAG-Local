"""Integración HTTP de CRUD KB (requiere TEST_DATABASE_URL)."""

from __future__ import annotations

import os
import uuid

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import clear_settings_cache, get_settings
from app.models.knowledge_base import KbMembership
from app.models.user import User
from app.services.passwords import hash_password
from tests.test_auth_integration import (
    _alembic_config,
    _ensure_database_exists,
    _reset_public_schema,
)


@pytest.fixture(scope="module")
def kb_postgres_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("Define TEST_DATABASE_URL para pruebas de integración de KB.")
    _ensure_database_exists(url)
    _reset_public_schema(url)
    cfg = _alembic_config(url)
    command.upgrade(cfg, "head")
    return url


@pytest.fixture
def kb_two_users_client(
    kb_postgres_url: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DATABASE_URL", kb_postgres_url)
    clear_settings_cache()
    settings = get_settings()
    engine = create_engine(kb_postgres_url)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    pwd = "kb-integration-test-9chars"
    email_a = f"kb_a_{uuid.uuid4().hex[:10]}@example.com"
    email_b = f"kb_b_{uuid.uuid4().hex[:10]}@example.com"
    with SessionLocal() as db:
        ua = User(
            email=email_a,
            password_hash=hash_password(pwd, pepper=settings.password_pepper),
            role="user",
            is_active=True,
        )
        ub = User(
            email=email_b,
            password_hash=hash_password(pwd, pepper=settings.password_pepper),
            role="user",
            is_active=True,
        )
        db.add_all([ua, ub])
        db.commit()
        id_b = str(ub.id)
    engine.dispose()

    from app.main import app

    with TestClient(app) as client:
        yield client, email_a, email_b, pwd, id_b
    clear_settings_cache()


def _login(client: TestClient, email: str, password: str) -> str:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_kb_crud_and_authorization(kb_two_users_client: tuple) -> None:
    client, email_a, email_b, pwd, id_b = kb_two_users_client

    token_a = _login(client, email_a, pwd)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    r_create = client.post(
        "/api/kbs",
        headers=headers_a,
        json={"name": "  Mi KB  ", "description": "  desc  "},
    )
    assert r_create.status_code == 201, r_create.text
    body_c = r_create.json()
    kb_id = body_c["id"]
    assert body_c["name"] == "  Mi KB  ".strip()
    assert body_c["description"] == "desc"

    r_list = client.get("/api/kbs", headers=headers_a)
    assert r_list.status_code == 200
    items = r_list.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == kb_id

    r_one = client.get(f"/api/kbs/{kb_id}", headers=headers_a)
    assert r_one.status_code == 200
    assert r_one.json()["name"] == "Mi KB"

    token_b = _login(client, email_b, pwd)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    r_forbidden = client.get(f"/api/kbs/{kb_id}", headers=headers_b)
    assert r_forbidden.status_code == 403
    assert r_forbidden.json()["error"]["code"] == "AUTH_FORBIDDEN"

    engine = create_engine(os.environ["DATABASE_URL"])
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with SessionLocal() as db:
        m = KbMembership(kb_id=uuid.UUID(kb_id), user_id=uuid.UUID(id_b), role="viewer")
        db.add(m)
        db.commit()
    engine.dispose()

    r_viewer = client.get(f"/api/kbs/{kb_id}", headers=headers_b)
    assert r_viewer.status_code == 200

    r_patch_denied = client.patch(
        f"/api/kbs/{kb_id}",
        headers=headers_b,
        json={"name": "Hacked"},
    )
    assert r_patch_denied.status_code == 403

    r_patch_ok = client.patch(
        f"/api/kbs/{kb_id}",
        headers=headers_a,
        json={"name": "Renombrada", "description": None},
    )
    assert r_patch_ok.status_code == 200
    assert r_patch_ok.json()["name"] == "Renombrada"
    assert r_patch_ok.json()["description"] is None

    r_del_b = client.delete(f"/api/kbs/{kb_id}", headers=headers_b)
    assert r_del_b.status_code == 403

    r_del = client.delete(f"/api/kbs/{kb_id}", headers=headers_a)
    assert r_del.status_code == 204

    r_gone = client.get(f"/api/kbs/{kb_id}", headers=headers_a)
    assert r_gone.status_code == 404

    r_list_empty = client.get("/api/kbs", headers=headers_a)
    assert r_list_empty.status_code == 200
    assert r_list_empty.json()["items"] == []

    r_aux = client.post("/api/kbs", headers=headers_a, json={"name": "Aux"})
    aux_id = r_aux.json()["id"]
    r_bad = client.patch(f"/api/kbs/{aux_id}", headers=headers_a, json={})
    assert r_bad.status_code == 422
    client.delete(f"/api/kbs/{aux_id}", headers=headers_a)
