"""Orquestación de embeddings con batching, normalización y backoff OOM."""

from __future__ import annotations

import logging
import math
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.document import Chunk, Document
from app.services.embeddings.errors import EmbeddingError, RecoverableEmbeddingError
from app.services.embeddings.fake import embed_texts_fake
from app.services.embeddings.sentence_transformer import embed_texts_sentence_transformer

logger = logging.getLogger(__name__)

__all__ = ["EmbeddingError", "embed_texts", "embed_document_chunks"]


def stable_qdrant_point_id(chunk_id: uuid.UUID) -> str:
    """ID estable para Qdrant (coincide con el UUID del chunk en Postgres)."""
    return str(chunk_id)


def embed_texts(texts: list[str], settings: Settings) -> list[list[float]]:
    """Genera vectores para una lista de textos con backoff de batch por OOM."""
    if not texts:
        return []
    if not settings.embedding_enabled:
        raise EmbeddingError("embedding_disabled", "Embeddings deshabilitados por configuración.")

    batch_size = settings.embedding_batch_size
    min_batch = settings.embedding_batch_size_min
    backend = settings.resolved_embedding_backend()

    while True:
        try:
            if backend == "fake":
                return embed_texts_fake(texts, settings)
            return embed_texts_sentence_transformer(
                texts,
                settings,
                batch_size=batch_size,
            )
        except RecoverableEmbeddingError as e:
            if e.code != "embedding_oom" or batch_size <= min_batch:
                raise
            next_batch = max(min_batch, batch_size // 2)
            logger.warning(
                "OOM en embeddings; reduciendo batch de %s a %s.",
                batch_size,
                next_batch,
            )
            batch_size = next_batch


def embed_document_chunks(
    session: Session,
    document: Document,
    settings: Settings,
) -> tuple[dict[str, Any], list[tuple[str, list[float]]]]:
    """Embedea chunks del documento, actualiza DB y devuelve métricas + vectores."""
    if not settings.embedding_enabled:
        return {"embedding_status": "skipped"}, []

    rows = session.scalars(
        select(Chunk)
        .where(Chunk.document_id == document.id)
        .order_by(Chunk.chunk_index)
    ).all()
    if not rows:
        raise EmbeddingError("chunk_missing", "No hay chunks para embeder.")

    texts = [c.text for c in rows]
    vectors = embed_texts(texts, settings)
    if len(vectors) != len(rows):
        raise EmbeddingError(
            "embedding_count_mismatch",
            "El número de vectores no coincide con chunks.",
        )

    dim = len(vectors[0]) if vectors else 0
    point_vectors: list[tuple[str, list[float]]] = []

    for chunk, vector in zip(rows, vectors, strict=True):
        point_id = stable_qdrant_point_id(chunk.id)
        chunk.embedding_model = settings.embedding_model_label
        chunk.qdrant_point_id = point_id
        meta = dict(chunk.chunk_metadata or {})
        meta["embedding_dim"] = dim
        meta["embedding_backend"] = settings.resolved_embedding_backend()
        if settings.embedding_normalize:
            meta["embedding_normalized"] = True
        chunk.chunk_metadata = meta
        session.add(chunk)
        point_vectors.append((point_id, vector))

    session.flush()

    metrics: dict[str, Any] = {
        "embedding_status": "done",
        "embedding_model": settings.embedding_model_label,
        "embedding_backend": settings.resolved_embedding_backend(),
        "embedding_count": len(rows),
        "embedding_dim": dim,
    }
    return metrics, point_vectors


def vector_l2_norm(vector: list[float]) -> float:
    return math.sqrt(sum(v * v for v in vector))
