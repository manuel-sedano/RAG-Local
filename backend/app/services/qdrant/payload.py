"""Payload de puntos Qdrant (esquema documentado en `docs/10-database-schema.md`)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings
from app.models.document import Chunk, Document

# Campos indexables / filtrables en payload (referencia para retrieval):
# kb_id, doc_id, chunk_id, owner_user_id, mime_type, tags, language, source,
# page_start, page_end, chunk_index, created_at, text (snippet opcional).


def normalize_tags(tags: dict | list | None) -> list[str]:
    if tags is None:
        return []
    if isinstance(tags, list):
        return [str(t) for t in tags if str(t).strip()]
    if isinstance(tags, dict):
        return [str(k) for k in tags if str(k).strip()]
    return []


def build_chunk_payload(document: Document, chunk: Chunk, settings: Settings) -> dict[str, Any]:
    snippet = ""
    if settings.qdrant_snippet_max_chars > 0:
        snippet = chunk.text[: settings.qdrant_snippet_max_chars]

    created_at = chunk.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    else:
        created_at = created_at.astimezone(UTC)

    owner_id: str | None = None
    if document.uploaded_by_user_id is not None:
        owner_id = str(document.uploaded_by_user_id)

    payload: dict[str, Any] = {
        "kb_id": str(document.kb_id),
        "doc_id": str(document.id),
        "chunk_id": str(chunk.id),
        "mime_type": document.mime_type,
        "tags": normalize_tags(document.tags),
        "language": document.language,
        "source": document.source,
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
        "page_start": chunk.page_start,
        "page_end": chunk.page_end,
        "chunk_index": chunk.chunk_index,
        "text": snippet,
    }
    if owner_id is not None:
        payload["owner_user_id"] = owner_id
    return payload


def parse_point_id(point_id: str | uuid.UUID) -> str:
    if isinstance(point_id, uuid.UUID):
        return str(point_id)
    return str(point_id)
