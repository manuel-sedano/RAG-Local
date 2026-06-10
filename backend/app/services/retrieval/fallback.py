"""Fallback de retrieval para preguntas meta sobre documentos (p. ej. «de qué va el PDF»)."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.document import Chunk, Document
from app.services.retrieval.filters import matches_filters
from app.services.retrieval.types import ChunkCandidate, SearchFilters, SearchHit

_OVERVIEW_VERB_RE = re.compile(
    r"(?i)(?:"
    r"de\s+qu[eé]\s+va|"
    r"qu[eé]\s+trata|"
    r"qu[eé]\s+dice|"
    r"de\s+qu[eé]\s+se\s+trata|"
    r"de\s+qu[eé]\s+habla|"
    r"resume(?:r|me)?(?:\s+el|\s+la|\s+los|\s+las)?|"
    r"resumen(?:\s+de|\s+del|\s+de\s+la)?|"
    r"summarize|"
    r"what\s+(?:is|'\s*s)\s+.+\s+about"
    r")"
)

_DOC_REF_RE = re.compile(
    r"(?i)(?:"
    r"pdf|documento|documentos|archivo|archivos|"
    r"docx?|fichero|ficheros|"
    r"\.pdf|\.docx?"
    r")"
)


def is_document_overview_query(query: str) -> bool:
    """True si el usuario pide un resumen o tema general del material indexado."""
    q = query.strip()
    if not q or len(q) > 200:
        return False
    if _OVERVIEW_VERB_RE.search(q):
        return True
    if _DOC_REF_RE.search(q) and re.search(
        r"(?i)(de\s+qu[eé]|qu[eé]|about|resume|resumen|trata|contenido|tema)",
        q,
    ):
        return True
    return False


def count_ready_chunks(session: Session, kb_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(Chunk)
            .join(Document, Chunk.document_id == Document.id)
            .where(
                Chunk.kb_id == kb_id,
                Document.kb_id == kb_id,
                Document.deleted_at.is_(None),
                Document.status == "READY",
            )
        )
        or 0
    )


def should_use_overview_fallback(
    session: Session,
    query: str,
    kb_id: uuid.UUID,
    settings: Settings,
) -> bool:
    if not settings.rag_overview_fallback_enabled:
        return False
    if not is_document_overview_query(query):
        return False
    return count_ready_chunks(session, kb_id) > 0


def _snippet(text: str, settings: Settings) -> str:
    max_chars = settings.qdrant_snippet_max_chars or 500
    if max_chars <= 0:
        return ""
    return text[:max_chars]


def overview_fallback_hits(
    session: Session,
    settings: Settings,
    *,
    kb_id: uuid.UUID,
    limit: int,
    filters: SearchFilters | None = None,
) -> list[SearchHit]:
    """Devuelve los primeros chunks indexados cuando la búsqueda semántica no encaja."""
    rows = session.execute(
        select(Chunk, Document)
        .join(Document, Chunk.document_id == Document.id)
        .where(
            Chunk.kb_id == kb_id,
            Document.kb_id == kb_id,
            Document.deleted_at.is_(None),
            Document.status == "READY",
        )
        .order_by(Document.created_at, Chunk.chunk_index)
        .limit(max(1, limit))
    ).all()

    hits: list[SearchHit] = []
    for chunk, doc in rows:
        if not (chunk.text or "").strip():
            continue
        cand = ChunkCandidate(
            chunk_id=chunk.id,
            doc_id=doc.id,
            kb_id=kb_id,
            text=chunk.text,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            mime_type=doc.mime_type,
            tags=list(doc.tags or []),
            source=doc.source,
        )
        if not matches_filters(cand, filters):
            continue
        page = chunk.page_start if chunk.page_start is not None else chunk.page_end
        hits.append(
            SearchHit(
                chunk_id=chunk.id,
                doc_id=doc.id,
                score=0.0,
                page=page,
                snippet=_snippet(chunk.text, settings),
                retrieval_score=0.0,
            )
        )
    return hits[:limit]
