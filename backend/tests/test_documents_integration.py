"""Integración HTTP de documentos (requiere TEST_DATABASE_URL)."""

from __future__ import annotations

import io
import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import clear_settings_cache, get_settings
from app.models.document import Document
from app.models.user import User
from app.services.passwords import hash_password
from tests.test_auth_integration import (
    _alembic_config,
    _ensure_database_exists,
    _reset_public_schema,
)


@pytest.fixture(scope="module")
def doc_postgres_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("Define TEST_DATABASE_URL para pruebas de integración de documentos.")
    _ensure_database_exists(url)
    _reset_public_schema(url)
    cfg = _alembic_config(url)
    command.upgrade(cfg, "head")
    return url


@pytest.fixture
def doc_client(
    doc_postgres_url: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    upload_root = tmp_path / "uploads_test"
    upload_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DATABASE_URL", doc_postgres_url)
    monkeypatch.setenv("UPLOAD_STORAGE_DIR", str(upload_root))
    monkeypatch.setenv("MAX_UPLOAD_MB", "5")
    clear_settings_cache()
    settings = get_settings()
    engine = create_engine(doc_postgres_url)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    pwd = "doc-integration-test-9"
    email = f"doc_u_{uuid.uuid4().hex[:10]}@example.com"
    with SessionLocal() as db:
        u = User(
            email=email,
            password_hash=hash_password(pwd, pepper=settings.password_pepper),
            role="user",
            is_active=True,
        )
        db.add(u)
        db.commit()
    engine.dispose()

    from app.main import app

    with TestClient(app) as client:
        yield client, email, pwd, upload_root
    clear_settings_cache()


def _login(client: TestClient, email: str, password: str) -> str:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _minimal_pdf() -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"xref\n0 3\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000052 00000 n \n"
        b"trailer\n<< /Size 3 /Root 1 0 R >>\n"
        b"startxref\n110\n%%EOF\n"
    )


def test_upload_list_download_delete(doc_client: tuple) -> None:
    client, email, pwd, upload_root = doc_client
    token = _login(client, email, pwd)
    h = {"Authorization": f"Bearer {token}"}

    r_kb = client.post("/api/kbs", headers=h, json={"name": "KB docs"})
    assert r_kb.status_code == 201, r_kb.text
    kb_id = r_kb.json()["id"]

    pdf = _minimal_pdf()
    files = {"file": ("reporte.pdf", io.BytesIO(pdf), "application/pdf")}
    r_up = client.post(
        f"/api/kbs/{kb_id}/documents/upload",
        headers=h,
        files=files,
        data={"tags": "a,b", "source": "test", "language": "es"},
    )
    assert r_up.status_code == 202, r_up.text
    body = r_up.json()
    doc_id = body["document_id"]
    assert body["status"] == "UPLOADED"
    assert "ingestion_job_id" in body

    r_list = client.get(f"/api/kbs/{kb_id}/documents", headers=h)
    assert r_list.status_code == 200
    items = r_list.json()["items"]
    assert len(items) == 1
    assert items[0]["filename_original"] == "reporte.pdf"

    r_get = client.get(f"/api/kbs/{kb_id}/documents/{doc_id}", headers=h)
    assert r_get.status_code == 200
    assert r_get.json()["tags"] == ["a", "b"]

    r_st = client.get(f"/api/kbs/{kb_id}/documents/{doc_id}/status", headers=h)
    assert r_st.status_code == 200
    assert r_st.json()["document_id"] == doc_id

    r_file = client.get(f"/api/kbs/{kb_id}/documents/{doc_id}/file", headers=h)
    assert r_file.status_code == 200
    assert r_file.content == pdf

    r_del = client.delete(f"/api/kbs/{kb_id}/documents/{doc_id}", headers=h)
    assert r_del.status_code == 204

    r_gone = client.get(f"/api/kbs/{kb_id}/documents/{doc_id}", headers=h)
    assert r_gone.status_code == 404


def test_upload_invalid_magic(doc_client: tuple) -> None:
    client, email, pwd, _ = doc_client
    token = _login(client, email, pwd)
    h = {"Authorization": f"Bearer {token}"}
    r_kb = client.post("/api/kbs", headers=h, json={"name": "KB2"})
    kb_id = r_kb.json()["id"]
    bad = b"not a pdf content"
    files = {"file": ("x.pdf", io.BytesIO(bad), "application/pdf")}
    r_up = client.post(f"/api/kbs/{kb_id}/documents/upload", headers=h, files=files)
    assert r_up.status_code == 415


def test_upload_oversized(doc_client: tuple, monkeypatch: pytest.MonkeyPatch) -> None:
    client, email, pwd, _ = doc_client
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    clear_settings_cache()
    token = _login(client, email, pwd)
    h = {"Authorization": f"Bearer {token}"}
    r_kb = client.post("/api/kbs", headers=h, json={"name": "KB3"})
    kb_id = r_kb.json()["id"]
    big = _minimal_pdf() + b"x" * 1_100_000
    files = {"file": ("big.pdf", io.BytesIO(big), "application/pdf")}
    r_up = client.post(f"/api/kbs/{kb_id}/documents/upload", headers=h, files=files)
    assert r_up.status_code == 413


def test_upload_duplicate_blocked(doc_client: tuple) -> None:
    client, email, pwd, _ = doc_client
    token = _login(client, email, pwd)
    h = {"Authorization": f"Bearer {token}"}
    r_kb = client.post("/api/kbs", headers=h, json={"name": "KB dup"})
    kb_id = r_kb.json()["id"]
    pdf = _minimal_pdf()
    files = {"file": ("a.pdf", io.BytesIO(pdf), "application/pdf")}
    r1 = client.post(f"/api/kbs/{kb_id}/documents/upload", headers=h, files=files)
    assert r1.status_code == 202
    r2 = client.post(
        f"/api/kbs/{kb_id}/documents/upload",
        headers=h,
        files={"file": ("b.pdf", io.BytesIO(pdf), "application/pdf")},
    )
    assert r2.status_code == 409


def test_quarantine_file_returns_409(doc_client: tuple) -> None:
    client, email, pwd, upload_root = doc_client
    token = _login(client, email, pwd)
    h = {"Authorization": f"Bearer {token}"}
    r_kb = client.post("/api/kbs", headers=h, json={"name": "KB q"})
    kb_id = r_kb.json()["id"]
    pdf = _minimal_pdf()
    files = {"file": ("q.pdf", io.BytesIO(pdf), "application/pdf")}
    r_up = client.post(f"/api/kbs/{kb_id}/documents/upload", headers=h, files=files)
    doc_id = r_up.json()["document_id"]

    eng = create_engine(os.environ["DATABASE_URL"])
    LocalSession = sessionmaker(bind=eng, autoflush=False, autocommit=False, expire_on_commit=False)
    with LocalSession() as db:
        row = db.get(Document, uuid.UUID(doc_id))
        assert row is not None
        row.status = "QUARANTINED"
        db.commit()
    eng.dispose()

    r_file = client.get(f"/api/kbs/{kb_id}/documents/{doc_id}/file", headers=h)
    assert r_file.status_code == 409
