"""Streaming de chat vía Socket.IO (mock sio + Postgres)."""

from __future__ import annotations

import os
import uuid
from typing import Any

import pytest
from alembic import command
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import clear_settings_cache, get_settings
from app.models.document import Chunk, Document
from app.services.chat.streaming import run_chat_stream_generation
from app.services.retrieval.bm25_index import refresh_kb_bm25_index
from tests.test_auth_integration import (
    _alembic_config,
    _ensure_database_exists,
    _reset_public_schema,
)


class RecordingSio:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def emit(
        self,
        event: str,
        data: dict[str, Any],
        *,
        room: str | None = None,
        namespace: str | None = None,
    ) -> None:
        _ = (room, namespace)
        self.events.append((event, data))


@pytest.fixture(scope="module")
def stream_postgres_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("Define TEST_DATABASE_URL para tests de streaming Socket.IO.")
    _ensure_database_exists(url)
    _reset_public_schema(url)
    cfg = _alembic_config(url)
    command.upgrade(cfg, "head")
    return url


@pytest.mark.asyncio
async def test_stream_emits_tokens_citations_and_done(
    stream_postgres_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", stream_postgres_url)
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("CHAT_LLM_BACKEND", "fake")
    monkeypatch.setenv("QDRANT_ENABLED", "false")
    clear_settings_cache()
    settings = get_settings()

    engine = create_engine(stream_postgres_url)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with SessionLocal() as db:
        from app.models.chat import Chat, ChatMessage
        from app.models.knowledge_base import KnowledgeBase
        from app.models.user import User
        from app.services.passwords import hash_password

        user = User(
            email=f"stream_{uuid.uuid4().hex[:8]}@example.com",
            password_hash=hash_password("pwd-stream-9chars", pepper=settings.password_pepper),
            role="user",
            is_active=True,
        )
        db.add(user)
        db.flush()
        kb = KnowledgeBase(name="KB Stream", owner_user_id=user.id)
        db.add(kb)
        db.flush()
        kb_id = kb.id
        chat = Chat(kb_id=kb_id, created_by_user_id=user.id, title="T")
        db.add(chat)
        db.flush()
        chat_id = chat.id
        db.add(
            ChatMessage(chat_id=chat_id, role="user", content="política de viáticos")
        )
        assistant = ChatMessage(chat_id=chat_id, role="assistant", content="")
        db.add(assistant)
        db.flush()
        assistant_id = assistant.id
        doc = Document(
            kb_id=kb_id,
            filename_original="manual.pdf",
            storage_path=f"{kb_id}/m.pdf",
            mime_type="application/pdf",
            size_bytes=10,
            sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            status="READY",
        )
        db.add(doc)
        db.flush()
        chunk = Chunk(
            document_id=doc.id,
            kb_id=kb_id,
            chunk_index=0,
            text="política de viáticos comprobantes supervisor",
            page_start=2,
            page_end=2,
            qdrant_point_id=str(uuid.uuid4()),
            embedding_model="fake",
        )
        db.add(chunk)
        db.commit()
        refresh_kb_bm25_index(db, kb_id, settings)

    sio = RecordingSio()
    with SessionLocal() as db:
        await run_chat_stream_generation(
            db,
            settings,
            sio,  # type: ignore[arg-type]
            kb_id=kb_id,
            chat_id=chat_id,
            assistant_message_id=assistant_id,
            user_content="política de viáticos",
            rag=None,
        )

    event_names = [e[0] for e in sio.events]
    assert "chat:citation" in event_names
    assert "chat:token" in event_names
    assert "chat:done" in event_names
    done = next(e for e in sio.events if e[0] == "chat:done")
    assert done[1]["status"] == "DONE"
    engine.dispose()
