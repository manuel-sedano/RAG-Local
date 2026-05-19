"""Prompting de chat RAG (unitario, sin DB)."""

from __future__ import annotations

import uuid

from app.core.config import get_settings
from app.services.chat.prompting import build_chat_messages, build_context_block, build_system_prompt
from app.services.retrieval.types import SearchHit


def test_system_prompt_spanish() -> None:
    settings = get_settings()
    assert "español" in build_system_prompt(settings).lower()


def test_context_block_empty() -> None:
    assert "Sin fragmentos" in build_context_block([], max_chars=1000)


def test_build_messages_includes_context() -> None:
    settings = get_settings()
    hit = SearchHit(
        chunk_id=uuid.uuid4(),
        doc_id=uuid.uuid4(),
        score=0.5,
        page=1,
        snippet="Política de viáticos",
    )
    ctx = build_context_block([hit], max_chars=5000)
    msgs = build_chat_messages(settings, user_query="¿Viáticos?", context_block=ctx)
    assert msgs[0]["role"] == "system"
    assert msgs[-1]["role"] == "user"
    assert "viáticos" in msgs[-1]["content"].lower()
