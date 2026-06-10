"""Integración POST /chats/{id}/messages con LLM fake y BM25."""

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
from app.models.user import User
from app.services.passwords import hash_password
from app.services.retrieval.bm25_index import refresh_kb_bm25_index
from tests.test_auth_integration import (
    _alembic_config,
    _ensure_database_exists,
    _reset_public_schema,
)


@pytest.fixture(scope="module")
def chat_rag_postgres_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("Define TEST_DATABASE_URL para pruebas de generación de chat.")
    _ensure_database_exists(url)
    _reset_public_schema(url)
    cfg = _alembic_config(url)
    command.upgrade(cfg, "head")
    return url


@pytest.fixture
def chat_rag_client(chat_rag_postgres_url: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", chat_rag_postgres_url)
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("CHAT_LLM_BACKEND", "fake")
    monkeypatch.setenv("QDRANT_ENABLED", "false")
    clear_settings_cache()
    settings = get_settings()
    engine = create_engine(chat_rag_postgres_url)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    pwd = "chat-rag-test-9chars-xx"
    email = f"chat_rag_{uuid.uuid4().hex[:10]}@example.com"
    with SessionLocal() as db:
        user = User(
            email=email,
            password_hash=hash_password(pwd, pepper=settings.password_pepper),
            role="user",
            is_active=True,
        )
        db.add(user)
        db.commit()
    engine.dispose()

    from app.main import app

    with TestClient(app) as client:
        yield client, email, pwd
    clear_settings_cache()


def _login(client: TestClient, email: str, password: str) -> str:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _create_kb_and_chat(client: TestClient, headers: dict) -> tuple[str, str]:
    r_kb = client.post("/api/kbs", headers=headers, json={"name": "KB RAG Chat"})
    assert r_kb.status_code == 201
    kb_id = r_kb.json()["id"]
    r_chat = client.post(
        f"/api/kbs/{kb_id}/chats",
        headers=headers,
        json={"title": "Prueba RAG"},
    )
    assert r_chat.status_code == 201
    return kb_id, r_chat.json()["chat_id"]


def test_post_message_no_evidence(chat_rag_client: tuple) -> None:
    client, email, pwd = chat_rag_client
    token = _login(client, email, pwd)
    headers = {"Authorization": f"Bearer {token}"}
    kb_id, chat_id = _create_kb_and_chat(client, headers)

    r = client.post(
        f"/api/kbs/{kb_id}/chats/{chat_id}/messages",
        headers=headers,
        json={"content": "¿Cuál es la política de viáticos?", "stream": False},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role"] == "assistant"
    assert "evidencia" in body["content"].lower()
    assert body["citations"] == []


def test_post_message_with_context_and_citations(chat_rag_client: tuple) -> None:
    client, email, pwd = chat_rag_client
    token = _login(client, email, pwd)
    headers = {"Authorization": f"Bearer {token}"}
    kb_id, chat_id = _create_kb_and_chat(client, headers)

    engine = create_engine(os.environ["DATABASE_URL"])
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    settings = get_settings()
    with SessionLocal() as db:
        doc = Document(
            kb_id=uuid.UUID(kb_id),
            filename_original="manual-viaticos.pdf",
            storage_path=f"{kb_id}/manual.pdf",
            mime_type="application/pdf",
            size_bytes=200,
            sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            tags=["finanzas"],
            status="READY",
        )
        db.add(doc)
        db.flush()
        chunk = Chunk(
            document_id=doc.id,
            kb_id=doc.kb_id,
            chunk_index=0,
            text="La política de viáticos exige comprobantes y autorización del supervisor.",
            page_start=3,
            page_end=3,
            qdrant_point_id=str(uuid.uuid4()),
            embedding_model="fake",
        )
        db.add(chunk)
        db.commit()
        refresh_kb_bm25_index(db, uuid.UUID(kb_id), settings)
        doc_id = str(doc.id)
        chunk_id = str(chunk.id)
    engine.dispose()

    r = client.post(
        f"/api/kbs/{kb_id}/chats/{chat_id}/messages",
        headers=headers,
        json={
            "content": "política de viáticos comprobantes",
            "stream": False,
            "rag": {"top_k": 5, "hybrid": True},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role"] == "assistant"
    assert "Fuentes" in body["content"] or "fragmentos" in body["content"].lower()
    assert len(body["citations"]) >= 1
    cite = body["citations"][0]
    assert cite["document_id"] == doc_id
    assert cite["chunk_id"] == chunk_id
    assert cite["filename_original"] == "manual-viaticos.pdf"
    assert cite["page_start"] == 3
    assert "/api/kbs/" in cite["file_path"]


def test_post_message_overview_pdf_query(chat_rag_client: tuple) -> None:
    client, email, pwd = chat_rag_client
    token = _login(client, email, pwd)
    headers = {"Authorization": f"Bearer {token}"}
    kb_id, chat_id = _create_kb_and_chat(client, headers)

    engine = create_engine(os.environ["DATABASE_URL"])
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    settings = get_settings()
    with SessionLocal() as db:
        doc = Document(
            kb_id=uuid.UUID(kb_id),
            filename_original="informe.pdf",
            storage_path=f"{kb_id}/informe.pdf",
            mime_type="application/pdf",
            size_bytes=200,
            sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            tags=["general"],
            status="READY",
        )
        db.add(doc)
        db.flush()
        chunk = Chunk(
            document_id=doc.id,
            kb_id=doc.kb_id,
            chunk_index=0,
            text="El informe presenta la estrategia comercial y los objetivos para el próximo año.",
            page_start=1,
            page_end=1,
            qdrant_point_id=str(uuid.uuid4()),
            embedding_model="fake",
        )
        db.add(chunk)
        db.commit()
        refresh_kb_bm25_index(db, uuid.UUID(kb_id), settings)
    engine.dispose()

    r = client.post(
        f"/api/kbs/{kb_id}/chats/{chat_id}/messages",
        headers=headers,
        json={"content": "de qué va el PDF", "stream": False},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role"] == "assistant"
    assert "evidencia" not in body["content"].lower()
    assert len(body["citations"]) >= 1


def test_post_message_stream_returns_202(chat_rag_client: tuple) -> None:
    client, email, pwd = chat_rag_client
    token = _login(client, email, pwd)
    headers = {"Authorization": f"Bearer {token}"}
    kb_id, chat_id = _create_kb_and_chat(client, headers)

    r = client.post(
        f"/api/kbs/{kb_id}/chats/{chat_id}/messages",
        headers=headers,
        json={"content": "Hola", "stream": True},
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "STREAMING"
    assert body["socket"]["namespace"] == "/chat"
