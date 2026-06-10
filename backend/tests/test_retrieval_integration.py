"""Integración HTTP de POST /api/kbs/{kb_id}/search (requiere TEST_DATABASE_URL)."""

from __future__ import annotations

import os
import uuid

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import clear_settings_cache, get_settings
from app.models.document import Chunk, Document
from app.models.knowledge_base import KbMembership, KnowledgeBase
from app.models.user import User
from app.services.embeddings.fake import embed_texts_fake
from app.services.passwords import hash_password
from app.services.qdrant.store import upsert_document_vectors
from app.services.retrieval import refresh_kb_bm25_index
from app.services.retrieval.bm25_index import clear_all_indexes
from tests.test_auth_integration import (
    _alembic_config,
    _ensure_database_exists,
    _reset_public_schema,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL", "").strip(),
    reason="Define TEST_DATABASE_URL para pruebas de integración de retrieval.",
)


@pytest.fixture(scope="module")
def retrieval_postgres_url() -> str:
    url = os.environ["TEST_DATABASE_URL"].strip()
    _ensure_database_exists(url)
    _reset_public_schema(url)
    cfg = _alembic_config(url)
    command.upgrade(cfg, "head")
    return url


@pytest.fixture
def retrieval_client(retrieval_postgres_url: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", retrieval_postgres_url)
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("QDRANT_ENABLED", "false")
    monkeypatch.setenv("RAG_HYBRID_ENABLED", "true")
    clear_settings_cache()
    clear_all_indexes()

    settings = get_settings()
    engine = create_engine(retrieval_postgres_url)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    pwd = "retrieval-test-9chars"
    email = f"retr_{uuid.uuid4().hex[:10]}@example.com"
    kb_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()

    with SessionLocal() as db:
        user = User(
            email=email,
            password_hash=hash_password(pwd, pepper=settings.password_pepper),
            role="user",
            is_active=True,
        )
        db.add(user)
        db.flush()
        kb = KnowledgeBase(
            id=kb_id,
            name="KB Retrieval",
            description="test",
            owner_user_id=user.id,
        )
        db.add(kb)
        db.add(KbMembership(kb_id=kb_id, user_id=user.id, role="owner"))
        doc = Document(
            id=doc_id,
            kb_id=kb_id,
            uploaded_by_user_id=user.id,
            filename_original="viaticos.pdf",
            storage_path=f"{kb_id}/{doc_id}.pdf",
            mime_type="application/pdf",
            size_bytes=100,
            sha256="c" * 64,
            language="es",
            source="viaticos.pdf",
            tags=["finanzas", "viaticos"],
            status="READY",
        )
        db.add(doc)
        chunk = Chunk(
            id=chunk_id,
            document_id=doc_id,
            kb_id=kb_id,
            chunk_index=0,
            text="La política de viáticos establece topes diarios para viajes corporativos.",
            page_start=3,
            page_end=3,
            embedding_model="bge-m3",
            qdrant_point_id=str(chunk_id),
        )
        db.add(chunk)
        db.commit()
        user_id = user.id

    with SessionLocal() as db:
        doc = db.get(Document, doc_id)
        ch = db.get(Chunk, chunk_id)
        assert doc is not None and ch is not None
        ch.qdrant_point_id = str(chunk_id)
        if os.environ.get("TEST_QDRANT_URL", "").strip():
            monkeypatch.setenv("QDRANT_ENABLED", "true")
            clear_settings_cache()
            settings = get_settings()
            vectors = embed_texts_fake(["viaticos corporativos"], settings)
            upsert_document_vectors(
                db,
                doc,
                [(str(chunk_id), vectors[0])],
                settings,
            )
        refresh_kb_bm25_index(db, kb_id, settings)
        db.commit()

    from app.main import app

    with TestClient(app) as client:
        login = client.post(
            "/api/auth/login",
            json={"email": email, "password": pwd},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        yield client, headers, kb_id, chunk_id, doc_id

    clear_all_indexes()
    clear_settings_cache()
    engine.dispose()


def test_search_bm25_viaticos(retrieval_client) -> None:
    client, headers, kb_id, chunk_id, _doc_id = retrieval_client
    resp = client.post(
        f"/api/kbs/{kb_id}/search",
        headers=headers,
        json={
            "query": "política de viáticos",
            "top_k": 5,
            "hybrid": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    items = body["items"]
    assert items
    assert items[0]["chunk_id"] == str(chunk_id)
    assert "viáticos" in items[0]["snippet"].lower() or "viaticos" in items[0]["snippet"].lower()
    assert body.get("metrics") is not None
    assert body["metrics"]["rerank_backend"] == "fake"


def test_search_overview_pdf_query(retrieval_client) -> None:
    client, headers, kb_id, chunk_id, _doc_id = retrieval_client
    resp = client.post(
        f"/api/kbs/{kb_id}/search",
        headers=headers,
        json={"query": "de qué va el PDF", "top_k": 5, "hybrid": True},
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert items
    assert items[0]["chunk_id"] == str(chunk_id)
    assert "viáticos" in items[0]["snippet"].lower() or "viaticos" in items[0]["snippet"].lower()


def test_search_filter_tags(retrieval_client) -> None:
    client, headers, kb_id, chunk_id, _doc_id = retrieval_client
    resp = client.post(
        f"/api/kbs/{kb_id}/search",
        headers=headers,
        json={
            "query": "viáticos",
            "filters": {"tags": ["legal"]},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["items"] == []

    resp_ok = client.post(
        f"/api/kbs/{kb_id}/search",
        headers=headers,
        json={
            "query": "viáticos",
            "filters": {"tags": ["finanzas"]},
        },
    )
    assert resp_ok.status_code == 200
    assert resp_ok.json()["items"][0]["chunk_id"] == str(chunk_id)


def test_search_forbidden_other_kb(retrieval_client) -> None:
    """403 cuando la KB existe pero el usuario no tiene membresía (no 404 por UUID inventado)."""
    client, headers, _kb_id, _chunk_id, _doc_id = retrieval_client
    other_kb_id = uuid.uuid4()
    settings = get_settings()
    engine = create_engine(os.environ["DATABASE_URL"])
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    with SessionLocal() as db:
        other_user = User(
            email=f"other_{uuid.uuid4().hex[:10]}@example.com",
            password_hash=hash_password("other-kb-pwd-9chars", pepper=settings.password_pepper),
            role="user",
            is_active=True,
        )
        db.add(other_user)
        db.flush()
        db.add(
            KnowledgeBase(
                id=other_kb_id,
                name="KB de otro usuario",
                description="sin acceso para el caller del test",
                owner_user_id=other_user.id,
            )
        )
        db.commit()
    engine.dispose()

    resp = client.post(
        f"/api/kbs/{other_kb_id}/search",
        headers=headers,
        json={"query": "viáticos"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "AUTH_FORBIDDEN"
