"""Filtrado de metadatos en candidatos de retrieval."""

from __future__ import annotations

from app.services.qdrant.payload import normalize_tags
from app.services.retrieval.types import ChunkCandidate, SearchFilters


def matches_filters(candidate: ChunkCandidate, filters: SearchFilters | None) -> bool:
    if filters is None:
        return True
    if filters.tags:
        tag_set = {t.lower() for t in candidate.tags}
        wanted = {t.lower() for t in filters.tags if str(t).strip()}
        if not wanted.intersection(tag_set):
            return False
    if filters.mime_types:
        allowed = {m.strip().lower() for m in filters.mime_types if m.strip()}
        if candidate.mime_type.lower() not in allowed:
            return False
    if filters.source is not None and filters.source.strip():
        src = (candidate.source or "").strip()
        if src != filters.source.strip():
            return False
    return True


def candidate_from_payload(payload: dict, *, snippet_max: int = 0) -> ChunkCandidate | None:
    import uuid

    try:
        chunk_id = uuid.UUID(str(payload["chunk_id"]))
        doc_id = uuid.UUID(str(payload["doc_id"]))
        kb_id = uuid.UUID(str(payload["kb_id"]))
    except (KeyError, ValueError, TypeError):
        return None
    text = str(payload.get("text") or "")
    return ChunkCandidate(
        chunk_id=chunk_id,
        doc_id=doc_id,
        kb_id=kb_id,
        text=text,
        page_start=payload.get("page_start"),
        page_end=payload.get("page_end"),
        mime_type=str(payload.get("mime_type") or ""),
        tags=normalize_tags(payload.get("tags")),
        source=payload.get("source"),
    )


def enrich_candidate_from_db(candidate: ChunkCandidate, *, text: str, tags, source, mime_type: str) -> ChunkCandidate:
    if text:
        candidate.text = text
    if tags is not None:
        candidate.tags = normalize_tags(tags)
    if source:
        candidate.source = source
    if mime_type:
        candidate.mime_type = mime_type
    return candidate
