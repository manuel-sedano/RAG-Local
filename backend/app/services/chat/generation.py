"""Generación RAG de respuestas de chat (retrieval + LLM + citas)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.models.chat import Chat, ChatMessage, MessageCitation
from app.models.document import Chunk
from app.services.chat.intent import is_conversational_message
from app.services.chat.prompt_guards import (
    assess_user_query,
    build_safety_flags,
    filter_search_hits,
)
from app.services.chat.prompting import build_chat_messages, build_context_block
from app.services.chat_service import touch_chat_updated_at
from app.services.ollama import (
    OllamaError,
    extract_usage,
    fake_chat_completion,
    generate_chat_token_pieces,
)
from app.services.retrieval import SearchFilters, hybrid_search
from app.services.retrieval.types import SearchHit

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RagRequestConfig:
    top_k: int | None = None
    rerank_top_k: int | None = None
    hybrid: bool | None = None
    filters: SearchFilters | None = None


@dataclass
class GeneratedReply:
    user_message: ChatMessage
    assistant_message: ChatMessage
    citations: list[MessageCitation]
    usage: dict[str, int] | None
    retrieval_hit_count: int


def _effective_top_k(settings: Settings, rag: RagRequestConfig | None) -> int:
    if rag and rag.rerank_top_k is not None:
        return rag.rerank_top_k
    if rag and rag.top_k is not None:
        return rag.top_k
    return settings.chat_default_top_k


def _load_chunk_pages(
    session: Session,
    hits: list[SearchHit],
) -> dict[uuid.UUID, tuple[int | None, int | None]]:
    if not hits:
        return {}
    ids = [h.chunk_id for h in hits]
    rows = session.execute(select(Chunk).where(Chunk.id.in_(ids))).scalars().all()
    return {c.id: (c.page_start, c.page_end) for c in rows}


def _persist_citations(
    session: Session,
    *,
    message_id: uuid.UUID,
    hits: list[SearchHit],
    page_map: dict[uuid.UUID, tuple[int | None, int | None]],
) -> list[MessageCitation]:
    citations: list[MessageCitation] = []
    for hit in hits:
        ps, pe = page_map.get(hit.chunk_id, (hit.page, hit.page))
        cit = MessageCitation(
            message_id=message_id,
            document_id=hit.doc_id,
            chunk_id=hit.chunk_id,
            score=float(hit.rerank_score if hit.rerank_score is not None else hit.score),
            page_start=ps if ps is not None else hit.page,
            page_end=pe if pe is not None else hit.page,
            snippet=(hit.snippet or "")[:2000] or None,
        )
        session.add(cit)
        citations.append(cit)
    session.flush()
    return citations


def _invoke_llm(
    settings: Settings,
    *,
    messages: list[dict[str, str]],
    user_query: str,
    hits: list[SearchHit],
) -> tuple[str, dict[str, int] | None]:
    backend = settings.resolved_chat_llm_backend()
    if backend == "fake":
        text, usage = fake_chat_completion(settings, user_query=user_query, hits=hits)
        return text, usage

    try:
        pieces, usage = generate_chat_token_pieces(settings, messages=messages)
        text = "".join(pieces).strip()
        if text:
            return text, usage
    except OllamaError:
        logger.exception("Ollama no disponible")

    logger.warning("Ollama sin respuesta; usando respaldo con fragmentos recuperados.")
    text, usage = fake_chat_completion(settings, user_query=user_query, hits=hits)
    return text, usage


def generate_chat_reply(
    session: Session,
    settings: Settings,
    *,
    chat: Chat,
    user_content: str,
    rag: RagRequestConfig | None = None,
    model: str | None = None,
) -> GeneratedReply:
    """Retrieval + LLM + persistencia de mensajes y citas (modo no-stream)."""
    content = user_content.strip()
    if not content:
        msg = "El mensaje no puede quedar vacío."
        raise ValueError(msg)

    user_guard = assess_user_query(content, settings)
    user_msg = ChatMessage(chat_id=chat.id, role="user", content=content)
    session.add(user_msg)
    session.flush()

    if user_guard.blocked:
        refusal = user_guard.refusal_message or (
            "No puedo ayudar con esa solicitud por políticas de seguridad."
        )
        assistant_msg = ChatMessage(
            chat_id=chat.id,
            role="assistant",
            content=refusal,
            model=settings.llm_model,
            safety_flags=build_safety_flags(user_guard=user_guard),
        )
        session.add(assistant_msg)
        session.flush()
        touch_chat_updated_at(session, chat)
        return GeneratedReply(
            user_message=user_msg,
            assistant_message=assistant_msg,
            citations=[],
            usage={"prompt_tokens": 0, "completion_tokens": len(refusal) // 4},
            retrieval_hit_count=0,
        )

    top_k = _effective_top_k(settings, rag)
    if is_conversational_message(content):
        hits: list[SearchHit] = []
        chunk_guard = filter_search_hits(hits, settings)
    else:
        search_result = hybrid_search(
            session,
            settings,
            kb_id=chat.kb_id,
            query=content,
            top_k=top_k,
            filters=rag.filters if rag else None,
            hybrid=rag.hybrid if rag else None,
            rerank=True,
        )
        chunk_guard = filter_search_hits(search_result.hits, settings)

    hits = chunk_guard.safe_hits
    safety_flags = build_safety_flags(chunk_guard=chunk_guard)

    context_block = build_context_block(
        hits,
        max_chars=settings.chat_context_max_chars,
    )
    history_rows = (
        session.execute(
            select(ChatMessage)
            .where(ChatMessage.chat_id == chat.id, ChatMessage.id != user_msg.id)
            .order_by(ChatMessage.created_at.asc())
        )
        .scalars()
        .all()
    )
    history = [(m.role, m.content) for m in history_rows if m.role in ("user", "assistant")]

    messages = build_chat_messages(
        settings,
        user_query=content,
        context_block=context_block,
        history=history,
    )

    _ = model  # reservado; Ollama usa settings.llm_model salvo override futuro
    assistant_text, usage = _invoke_llm(
        settings,
        messages=messages,
        user_query=content,
        hits=hits,
    )

    rag_config: dict[str, Any] = {
        "top_k": top_k,
        "hybrid": rag.hybrid if rag else None,
        "hit_count": len(hits),
        "ignored_chunks": len(chunk_guard.ignored_chunk_ids),
    }

    assistant_msg = ChatMessage(
        chat_id=chat.id,
        role="assistant",
        content=assistant_text,
        model=settings.llm_model,
        rag_config=rag_config,
        message_usage=usage,
        safety_flags=safety_flags,
    )
    session.add(assistant_msg)
    session.flush()

    page_map = _load_chunk_pages(session, hits)
    _persist_citations(
        session,
        message_id=assistant_msg.id,
        hits=hits,
        page_map=page_map,
    )
    citations = list(
        session.execute(
            select(MessageCitation)
            .where(MessageCitation.message_id == assistant_msg.id)
            .options(selectinload(MessageCitation.document))
        )
        .scalars()
        .all()
    )

    touch_chat_updated_at(session, chat)

    return GeneratedReply(
        user_message=user_msg,
        assistant_message=assistant_msg,
        citations=citations,
        usage=usage,
        retrieval_hit_count=len(hits),
    )
