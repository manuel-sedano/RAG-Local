"""Tipos compartidos de retrieval."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchFilters:
    """Filtros opcionales de metadatos (kb_id siempre se fuerza en servidor)."""

    tags: list[str] = field(default_factory=list)
    mime_types: list[str] = field(default_factory=list)
    source: str | None = None


@dataclass
class ChunkCandidate:
    chunk_id: uuid.UUID
    doc_id: uuid.UUID
    kb_id: uuid.UUID
    text: str
    page_start: int | None
    page_end: int | None
    mime_type: str
    tags: list[str]
    source: str | None
    vector_score: float | None = None
    bm25_score: float | None = None
    rrf_score: float = 0.0


@dataclass
class SearchHit:
    chunk_id: uuid.UUID
    doc_id: uuid.UUID
    score: float
    page: int | None
    snippet: str
    vector_score: float | None = None
    bm25_score: float | None = None
