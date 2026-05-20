"""Integración HTTP de chats por KB (requiere TEST_DATABASE_URL)."""

from __future__ import annotations

import os
import uuid

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import clear_settings_cache, get_settings
from app.models.chat import ChatMessage, MessageCitation
from app.models.document import Chunk, Document
from app.models.knowledge_base import KbMembership
from app.models.user import User
from app.services.passwords import hash_password
from tests.test_auth_integration import (
    _alembic_config,
    _ensure_database_exists,
    _reset_public_schema,
)


@pytest.fixture(scope="module")
def chat_postgres_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("Define TEST_DATABASE_URL para pruebas de integración de chats.")
    _ensure_database_exists(url)
    _reset_public_schema(url)
    cfg = _alembic_config(url)
    command.upgrade(cfg, "head")
    return url


@pytest.fixture
def chat_two_users_client(
    chat_postgres_url: str,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DATABASE_URL", chat_postgres_url)
    clear_settings_cache()
    settings = get_settings()
    engine = create_engine(chat_postgres_url)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    pwd = "chat-integration-test-9chars"
    email_a = f"chat_a_{uuid.uuid4().hex[:10]}@example.com"
    email_b = f"chat_b_{uuid.uuid4().hex[:10]}@example.com"
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
        id_a = str(ua.id)
        id_b = str(ub.id)
    engine.dispose()

    from app.main import app

    with TestClient(app) as client:
        yield client, email_a, email_b, pwd, id_a, id_b
    clear_settings_cache()


def _login(client: TestClient, email: str, password: str) -> str:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_chat_crud_and_authorization(chat_two_users_client: tuple) -> None:
    client, email_a, email_b, pwd, _id_a, id_b = chat_two_users_client

    token_a = _login(client, email_a, pwd)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    r_kb = client.post(
        "/api/kbs",
        headers=headers_a,
        json={"name": "KB Chat", "description": "pruebas"},
    )
    assert r_kb.status_code == 201, r_kb.text
    kb_id = r_kb.json()["id"]

    r_create = client.post(
        f"/api/kbs/{kb_id}/chats",
        headers=headers_a,
        json={"title": "  Consulta viáticos  "},
    )
    assert r_create.status_code == 201, r_create.text
    body_c = r_create.json()
    chat_id = body_c["chat_id"]
    assert body_c["title"] == "Consulta viáticos"
    assert "created_at" in body_c

    r_list = client.get(f"/api/kbs/{kb_id}/chats", headers=headers_a)
    assert r_list.status_code == 200
    items = r_list.json()["items"]
    assert len(items) == 1
    assert items[0]["chat_id"] == chat_id
    assert items[0]["title"] == "Consulta viáticos"

    r_detail = client.get(f"/api/kbs/{kb_id}/chats/{chat_id}", headers=headers_a)
    assert r_detail.status_code == 200
    detail = r_detail.json()
    assert detail["chat_id"] == chat_id
    assert detail["kb_id"] == kb_id
    assert detail["title"] == "Consulta viáticos"

    r_msgs_empty = client.get(
        f"/api/kbs/{kb_id}/chats/{chat_id}/messages",
        headers=headers_a,
    )
    assert r_msgs_empty.status_code == 200
    assert r_msgs_empty.json()["items"] == []

    token_b = _login(client, email_b, pwd)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    r_forbidden = client.get(f"/api/kbs/{kb_id}/chats", headers=headers_b)
    assert r_forbidden.status_code == 403
    assert r_forbidden.json()["error"]["code"] == "AUTH_FORBIDDEN"

    engine = create_engine(os.environ["DATABASE_URL"])
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with SessionLocal() as db:
        m = KbMembership(kb_id=uuid.UUID(kb_id), user_id=uuid.UUID(id_b), role="viewer")
        db.add(m)
        db.commit()
    engine.dispose()

    r_viewer_list = client.get(f"/api/kbs/{kb_id}/chats", headers=headers_b)
    assert r_viewer_list.status_code == 200
    assert len(r_viewer_list.json()["items"]) == 1

    r_viewer_create = client.post(
        f"/api/kbs/{kb_id}/chats",
        headers=headers_b,
        json={"title": "Chat de B"},
    )
    assert r_viewer_create.status_code == 201

    r_bad_chat = client.get(
        f"/api/kbs/{kb_id}/chats/{uuid.uuid4()}",
        headers=headers_a,
    )
    assert r_bad_chat.status_code == 404
    assert r_bad_chat.json()["error"]["code"] == "CHAT_NOT_FOUND"


def test_chat_messages_with_citations(chat_two_users_client: tuple) -> None:
    client, email_a, _, pwd, id_a, _ = chat_two_users_client
    token = _login(client, email_a, pwd)
    headers = {"Authorization": f"Bearer {token}"}

    r_kb = client.post("/api/kbs", headers=headers, json={"name": "KB Citas"})
    kb_id = r_kb.json()["id"]

    r_chat = client.post(
        f"/api/kbs/{kb_id}/chats",
        headers=headers,
        json={"title": "Con citas"},
    )
    chat_id = r_chat.json()["chat_id"]

    engine = create_engine(os.environ["DATABASE_URL"])
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with SessionLocal() as db:
        doc = Document(
            kb_id=uuid.UUID(kb_id),
            uploaded_by_user_id=uuid.UUID(id_a),
            filename_original="manual.pdf",
            storage_path="kb/test/manual.pdf",
            mime_type="application/pdf",
            size_bytes=100,
            sha256="a" * 64,
            status="READY",
        )
        db.add(doc)
        db.flush()
        chunk = Chunk(
            document_id=doc.id,
            kb_id=doc.kb_id,
            chunk_index=0,
            text="Política de viáticos",
            page_start=3,
            page_end=3,
            qdrant_point_id=str(uuid.uuid4()),
            embedding_model="fake",
        )
        db.add(chunk)
        db.flush()
        user_msg = ChatMessage(chat_id=uuid.UUID(chat_id), role="user", content="¿Viáticos?")
        asst_msg = ChatMessage(
            chat_id=uuid.UUID(chat_id),
            role="assistant",
            content="Según el documento...",
        )
        db.add_all([user_msg, asst_msg])
        db.flush()
        db.add(
            MessageCitation(
                message_id=asst_msg.id,
                document_id=doc.id,
                chunk_id=chunk.id,
                score=0.81,
                page_start=3,
                page_end=3,
                snippet="Política de viáticos",
            )
        )
        db.commit()
    engine.dispose()

    r_msgs = client.get(
        f"/api/kbs/{kb_id}/chats/{chat_id}/messages",
        headers=headers,
    )
    assert r_msgs.status_code == 200
    items = r_msgs.json()["items"]
    assert len(items) == 2
    assert items[0]["role"] == "user"
    assert items[0].get("citations") is None
    assert items[1]["role"] == "assistant"
    cites = items[1]["citations"]
    assert len(cites) == 1
    c0 = cites[0]
    assert c0["filename_original"] == "manual.pdf"
    assert c0["mime_type"] == "application/pdf"
    assert c0["page_start"] == 3
    assert f"/kbs/{kb_id}/documents/" in c0["viewer_path"]
    assert "?page=3" in c0["viewer_path"]
    assert c0["file_path"] == f"/api/kbs/{kb_id}/documents/{c0['document_id']}/file"
