"""Generación RAG con streaming vía Socket.IO."""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import socketio
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.models.chat import ChatMessage, MessageCitation
from app.realtime.emitters import emit_chat_citation, emit_chat_done, emit_chat_token
from app.services.chat.citations_serializer import citation_to_dict
from app.services.chat.generation import (
    RagRequestConfig,
    _effective_top_k,
    _load_chunk_pages,
    _persist_citations,
)
from app.services.chat.intent import is_conversational_message
from app.services.chat.prompting import build_chat_messages, build_context_block
from app.services.chat_service import get_chat_for_kb, touch_chat_updated_at
from app.services.ollama import (
    OllamaError,
    chat_completion,
    chat_completion_stream,
    extract_assistant_text,
    generate_chat_token_pieces,
)
from app.services.ollama.fake import fake_chat_completion
from app.services.retrieval import hybrid_search

logger = logging.getLogger(__name__)


@dataclass
class StreamPrepResult:
    chat_id: uuid.UUID
    message_id: uuid.UUID
    cite_payload: list[dict[str, Any]]
    messages: list[dict[str, str]]
    user_query: str
    valid_hits: list
    top_k: int
    rag_hybrid: bool | None


@dataclass
class StreamGenResult:
    chat_id: uuid.UUID
    message_id: uuid.UUID
    tokens: list[str]
    cite_payload: list[dict[str, Any]]


async def _iter_llm_token_pieces(
    settings: Settings,
    *,
    messages: list[dict[str, str]],
    user_query: str,
    hits: list,
) -> AsyncIterator[str]:
    """Fragmentos de texto en tiempo real (fake u Ollama)."""
    backend = settings.resolved_chat_llm_backend()
    if backend == "fake":
        text, _ = fake_chat_completion(settings, user_query=user_query, hits=hits)
        for word in text.split():
            if word:
                yield word + " "
                await asyncio.sleep(0)
        return

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    def _ollama_producer() -> None:
        got_any = False
        try:
            try:
                for piece in chat_completion_stream(settings, messages=messages):
                    if piece:
                        got_any = True
                        loop.call_soon_threadsafe(queue.put_nowait, piece)
            except OllamaError:
                logger.exception("Ollama stream falló")
            if not got_any:
                try:
                    raw = chat_completion(settings, messages=messages, stream=False)
                    text = extract_assistant_text(raw)
                    if text:
                        got_any = True
                        for word in text.split():
                            if word:
                                loop.call_soon_threadsafe(queue.put_nowait, word + " ")
                except OllamaError:
                    logger.exception("Ollama /api/chat sin stream falló")
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    threading.Thread(target=_ollama_producer, daemon=True).start()
    got_any = False
    while True:
        piece = await queue.get()
        if piece is None:
            break
        got_any = True
        yield piece
        await asyncio.sleep(0)

    if not got_any:
        logger.error(
            "Ollama no generó respuesta (modelo=%s); usando resumen de fragmentos",
            settings.llm_model,
        )
        text, _ = fake_chat_completion(settings, user_query=user_query, hits=hits)
        for word in text.split():
            if word:
                yield word + " "
                await asyncio.sleep(0)


def run_chat_stream_prepare_sync(
    session: Session,
    settings: Settings,
    *,
    kb_id: uuid.UUID,
    chat_id: uuid.UUID,
    assistant_message_id: uuid.UUID,
    user_content: str,
    rag: RagRequestConfig | None = None,
) -> StreamPrepResult:
    """Retrieval + citas + prompt (sin LLM)."""
    chat = get_chat_for_kb(session, kb_id=kb_id, chat_id=chat_id)
    if chat is None:
        msg = "Chat no encontrado."
        raise ValueError(msg)

    assistant_msg = session.get(ChatMessage, assistant_message_id)
    if assistant_msg is None:
        msg = "Mensaje assistant no encontrado."
        raise ValueError(msg)

    content = user_content.strip()
    top_k = _effective_top_k(settings, rag)

    if is_conversational_message(content):
        hits = []
        valid_hits: list = []
        page_map = {}
    else:
        search_result = hybrid_search(
            session,
            settings,
            kb_id=kb_id,
            query=content,
            top_k=top_k,
            filters=rag.filters if rag else None,
            hybrid=rag.hybrid if rag else None,
            rerank=True,
        )
        hits = search_result.hits
        page_map = _load_chunk_pages(session, hits)
        valid_hits = [h for h in hits if h.chunk_id in page_map]
        if len(valid_hits) < len(hits):
            logger.warning(
                "Se omitieron %s hits sin chunk en Postgres (chat_id=%s)",
                len(hits) - len(valid_hits),
                chat_id,
            )

    context_block = build_context_block(
        valid_hits,
        max_chars=settings.chat_context_max_chars,
    )
    history_rows = (
        session.execute(
            select(ChatMessage)
            .where(
                ChatMessage.chat_id == chat.id,
                ChatMessage.id != assistant_message_id,
            )
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

    _persist_citations(
        session,
        message_id=assistant_msg.id,
        hits=valid_hits,
        page_map=page_map,
    )
    session.commit()

    citations = list(
        session.execute(
            select(MessageCitation)
            .where(MessageCitation.message_id == assistant_msg.id)
            .options(selectinload(MessageCitation.document))
        )
        .scalars()
        .all()
    )
    cite_payload: list[dict[str, Any]] = []
    for c in citations:
        try:
            cite_payload.append(citation_to_dict(kb_id, c))
        except Exception:
            logger.warning(
                "Cita omitida message_id=%s chunk_id=%s (documento no disponible)",
                assistant_msg.id,
                c.chunk_id,
            )

    return StreamPrepResult(
        chat_id=chat_id,
        message_id=assistant_msg.id,
        cite_payload=cite_payload,
        messages=messages,
        user_query=content,
        valid_hits=valid_hits,
        top_k=top_k,
        rag_hybrid=rag.hybrid if rag else None,
    )


def run_chat_stream_finalize_sync(
    session: Session,
    settings: Settings,
    prep: StreamPrepResult,
    tokens: list[str],
) -> None:
    """Persiste el mensaje assistant tras el stream."""
    chat = get_chat_for_kb(session, kb_id=prep.chat_id, chat_id=prep.chat_id)
    assistant_msg = session.get(ChatMessage, prep.message_id)
    if chat is None or assistant_msg is None:
        return

    assistant_msg.content = "".join(tokens).strip()
    assistant_msg.model = settings.llm_model
    assistant_msg.rag_config = {
        "top_k": prep.top_k,
        "hybrid": prep.rag_hybrid,
        "hit_count": len(prep.valid_hits),
        "stream": True,
    }
    _, usage = fake_chat_completion(
        settings,
        user_query=prep.user_query,
        hits=prep.valid_hits,
    )
    assistant_msg.message_usage = usage
    touch_chat_updated_at(session, chat)
    session.commit()


async def _stream_llm_and_emit(
    sio: socketio.AsyncServer,
    settings: Settings,
    prep: StreamPrepResult,
) -> list[str]:
    tokens: list[str] = []
    async for piece in _iter_llm_token_pieces(
        settings,
        messages=prep.messages,
        user_query=prep.user_query,
        hits=prep.valid_hits,
    ):
        tokens.append(piece)
        await emit_chat_token(
            sio,
            chat_id=prep.chat_id,
            message_id=prep.message_id,
            token=piece,
        )
    return tokens


async def _run_stream_pipeline(
    sio: socketio.AsyncServer,
    settings: Settings,
    factory: Any,
    *,
    kb_id: uuid.UUID,
    chat_id: uuid.UUID,
    assistant_message_id: uuid.UUID,
    user_content: str,
    rag: RagRequestConfig | None,
) -> None:
    def _prepare() -> StreamPrepResult:
        with factory() as db:
            return run_chat_stream_prepare_sync(
                db,
                settings,
                kb_id=kb_id,
                chat_id=chat_id,
                assistant_message_id=assistant_message_id,
                user_content=user_content,
                rag=rag,
            )

    prep = await asyncio.to_thread(_prepare)

    if prep.cite_payload:
        await emit_chat_citation(
            sio,
            message_id=prep.message_id,
            citations=prep.cite_payload,
            chat_id=prep.chat_id,
        )

    tokens = await _stream_llm_and_emit(sio, settings, prep)

    def _finalize() -> None:
        with factory() as db:
            run_chat_stream_finalize_sync(db, settings, prep, tokens)

    await asyncio.to_thread(_finalize)

    logger.info(
        "Stream chat_id=%s message_id=%s tokens=%s hits=%s",
        prep.chat_id,
        prep.message_id,
        len(tokens),
        len(prep.valid_hits),
    )

    await emit_chat_done(
        sio,
        chat_id=prep.chat_id,
        message_id=prep.message_id,
        status="DONE",
    )


def run_chat_stream_sync(
    session: Session,
    settings: Settings,
    *,
    kb_id: uuid.UUID,
    chat_id: uuid.UUID,
    assistant_message_id: uuid.UUID,
    user_content: str,
    rag: RagRequestConfig | None = None,
) -> StreamGenResult:
    """Retrieval + LLM + persistencia (síncrono; tests)."""
    prep = run_chat_stream_prepare_sync(
        session,
        settings,
        kb_id=kb_id,
        chat_id=chat_id,
        assistant_message_id=assistant_message_id,
        user_content=user_content,
        rag=rag,
    )

    tokens: list[str] = []
    if settings.resolved_chat_llm_backend() != "fake":
        tokens, _ = generate_chat_token_pieces(settings, messages=prep.messages)

    if not tokens:
        text, _ = fake_chat_completion(
            settings,
            user_query=prep.user_query,
            hits=prep.valid_hits,
        )
        tokens = [w + " " for w in text.split() if w]

    run_chat_stream_finalize_sync(session, settings, prep, tokens)

    return StreamGenResult(
        chat_id=prep.chat_id,
        message_id=prep.message_id,
        tokens=tokens,
        cite_payload=prep.cite_payload,
    )


async def run_chat_stream_generation(
    session: Session,
    settings: Settings,
    sio: socketio.AsyncServer,
    *,
    kb_id: uuid.UUID,
    chat_id: uuid.UUID,
    assistant_message_id: uuid.UUID,
    user_content: str,
    rag: RagRequestConfig | None = None,
) -> None:
    """Emite eventos Socket.IO (tests de integración)."""
    _ = session
    from app.db.session import get_session_factory

    factory = get_session_factory()
    try:
        await _run_stream_pipeline(
            sio,
            settings,
            factory,
            kb_id=kb_id,
            chat_id=chat_id,
            assistant_message_id=assistant_message_id,
            user_content=user_content,
            rag=rag,
        )
    except Exception as e:
        logger.exception("Error en streaming chat_id=%s", chat_id)
        await emit_chat_done(
            sio,
            chat_id=chat_id,
            message_id=assistant_message_id,
            status="ERROR",
            error=str(e),
        )


def _log_stream_task_result(task: asyncio.Task[None]) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.exception("Tarea de streaming de chat falló", exc_info=exc)


async def start_chat_stream_task(
    app: Any,
    *,
    kb_id: uuid.UUID,
    chat_id: uuid.UUID,
    assistant_message_id: uuid.UUID,
    user_content: str,
    rag: RagRequestConfig | None,
) -> None:
    """Tarea en background tras POST /messages con stream=true."""
    sio = getattr(app.state, "sio", None)
    if sio is None:
        logger.error(
            "Socket.IO no inicializado (¿arrancaste con uvicorn app.main:asgi_application?)."
        )
        return
    settings = get_settings()
    factory = getattr(app.state, "db_session_factory", None)
    if factory is None:
        from app.db.session import get_session_factory

        factory = get_session_factory()

    logger.info(
        "Iniciando stream chat_id=%s assistant_message_id=%s",
        chat_id,
        assistant_message_id,
    )

    try:
        await _run_stream_pipeline(
            sio,
            settings,
            factory,
            kb_id=kb_id,
            chat_id=chat_id,
            assistant_message_id=assistant_message_id,
            user_content=user_content,
            rag=rag,
        )
    except Exception as e:
        logger.exception("Error en streaming chat_id=%s", chat_id)
        await emit_chat_done(
            sio,
            chat_id=chat_id,
            message_id=assistant_message_id,
            status="ERROR",
            error=str(e),
        )


def schedule_chat_stream_task(
    app: Any,
    *,
    kb_id: uuid.UUID,
    chat_id: uuid.UUID,
    assistant_message_id: uuid.UUID,
    user_content: str,
    rag: RagRequestConfig | None,
) -> None:
    """Programa la generación en el event loop activo."""
    task = asyncio.create_task(
        start_chat_stream_task(
            app,
            kb_id=kb_id,
            chat_id=chat_id,
            assistant_message_id=assistant_message_id,
            user_content=user_content,
            rag=rag,
        )
    )
    task.add_done_callback(_log_stream_task_result)
