"""Índice BM25 en memoria por KB (MVP)."""

from __future__ import annotations

import logging
import re
import threading
import uuid
from dataclasses import dataclass, field

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.document import Chunk, Document
from app.services.qdrant.payload import normalize_tags
from app.services.retrieval.types import ChunkCandidate

logger = logging.getLogger(__name__)

# Palabras y códigos con guiones (p. ej. NOM-035, NOM-035-STPS-2018).
_HYPHEN_TOKEN_RE = re.compile(
    r"[A-Za-zÀ-ÿ0-9]+(?:-[A-Za-zÀ-ÿ0-9]+)*",
    re.UNICODE,
)

_registry_lock = threading.Lock()
_kb_indexes: dict[uuid.UUID, "KbBm25Index"] = {}


@dataclass
class KbBm25Index:
    kb_id: uuid.UUID
    candidates: dict[uuid.UUID, ChunkCandidate] = field(default_factory=dict)
    corpus_ids: list[uuid.UUID] = field(default_factory=list)
    tokenized_corpus: list[list[str]] = field(default_factory=list)
    bm25: BM25Okapi | None = None


def tokenize(text: str) -> list[str]:
    """Tokeniza conservando acentos y expandiendo códigos con guiones en partes."""
    tokens: list[str] = []
    seen: set[str] = set()
    for match in _HYPHEN_TOKEN_RE.finditer(text):
        full = match.group(0).lower()
        for piece in (full, *full.split("-")) if "-" in full else (full,):
            if piece and piece not in seen:
                seen.add(piece)
                tokens.append(piece)
    return tokens


def _get_or_create_index(kb_id: uuid.UUID) -> KbBm25Index:
    with _registry_lock:
        if kb_id not in _kb_indexes:
            _kb_indexes[kb_id] = KbBm25Index(kb_id=kb_id)
        return _kb_indexes[kb_id]


def clear_kb_index(kb_id: uuid.UUID) -> None:
    with _registry_lock:
        _kb_indexes.pop(kb_id, None)


def clear_all_indexes() -> None:
    """Útil en tests para aislar estado."""
    with _registry_lock:
        _kb_indexes.clear()


def refresh_kb_bm25_index(session: Session, kb_id: uuid.UUID, settings: Settings) -> int:
    """Reconstruye el índice BM25 de una KB desde chunks de documentos READY."""
    rows = session.execute(
        select(Chunk, Document)
        .join(Document, Chunk.document_id == Document.id)
        .where(
            Chunk.kb_id == kb_id,
            Document.kb_id == kb_id,
            Document.deleted_at.is_(None),
            Document.status == "READY",
        )
        .order_by(Chunk.chunk_index)
    ).all()

    index = _get_or_create_index(kb_id)
    index.candidates.clear()
    index.corpus_ids.clear()
    index.tokenized_corpus.clear()
    index.bm25 = None

    for chunk, doc in rows:
        cand = ChunkCandidate(
            chunk_id=chunk.id,
            doc_id=doc.id,
            kb_id=kb_id,
            text=chunk.text,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            mime_type=doc.mime_type,
            tags=normalize_tags(doc.tags),
            source=doc.source,
        )
        tokens = tokenize(chunk.text)
        if not tokens:
            continue
        index.candidates[chunk.id] = cand
        index.corpus_ids.append(chunk.id)
        index.tokenized_corpus.append(tokens)

    if index.tokenized_corpus:
        index.bm25 = BM25Okapi(index.tokenized_corpus)

    logger.info(
        "BM25 index refreshed kb_id=%s chunks=%s",
        kb_id,
        len(index.corpus_ids),
    )
    return len(index.corpus_ids)


def bm25_search(
    kb_id: uuid.UUID,
    query: str,
    *,
    top_k: int,
    settings: Settings,
) -> list[tuple[ChunkCandidate, float]]:
    index = _get_or_create_index(kb_id)
    if index.bm25 is None or not index.corpus_ids:
        return []

    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    scores = index.bm25.get_scores(query_tokens)
    ranked = sorted(
        zip(index.corpus_ids, scores, strict=True),
        key=lambda x: x[1],
        reverse=True,
    )[:top_k]

    out: list[tuple[ChunkCandidate, float]] = []
    for chunk_id, score in ranked:
        cand = index.candidates.get(chunk_id)
        if cand is None:
            continue
        # BM25Okapi puede devolver 0 o negativo en corpus muy pequeño; aún rankeamos.
        if score <= 0 and out:
            continue
        out.append((cand, float(score)))
    return out
