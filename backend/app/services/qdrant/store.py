"""Upsert, búsqueda y borrado de vectores por documento/KB."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.document import Chunk, Document
from app.services.qdrant.client import get_qdrant_client
from app.services.qdrant.collection import ensure_collection
from app.services.qdrant.errors import QdrantStoreError
from app.services.qdrant.payload import build_chunk_payload, parse_point_id
from app.services.qdrant.search import vector_search

logger = logging.getLogger(__name__)


def _wrap_qdrant_errors(fn, *, code: str):
    try:
        return fn()
    except QdrantStoreError:
        raise
    except UnexpectedResponse as e:
        raise QdrantStoreError(code, str(e)) from e
    except Exception as e:
        raise QdrantStoreError(code, str(e)) from e


def upsert_document_vectors(
    session: Session,
    document: Document,
    point_vectors: list[tuple[str, list[float]]],
    settings: Settings,
) -> dict[str, Any]:
    """Upsert de chunks embedidos en la colección global."""
    if not settings.qdrant_enabled:
        return {"qdrant_status": "skipped", "qdrant_upsert_count": 0}

    if not point_vectors:
        return {"qdrant_status": "skipped", "qdrant_upsert_count": 0}

    vector_size = len(point_vectors[0][1])
    vectors_by_id = {parse_point_id(pid): vec for pid, vec in point_vectors}
    point_ids = list(vectors_by_id.keys())

    def _run() -> dict[str, Any]:
        client = get_qdrant_client(settings)
        ensure_collection(client, settings, vector_size)

        chunks = session.scalars(
            select(Chunk)
            .where(
                Chunk.document_id == document.id,
                Chunk.qdrant_point_id.in_(point_ids),
            )
            .order_by(Chunk.chunk_index)
        ).all()

        points: list[PointStruct] = []
        for chunk in chunks:
            pid = chunk.qdrant_point_id
            if pid is None or pid not in vectors_by_id:
                continue
            payload = build_chunk_payload(document, chunk, settings)
            points.append(
                PointStruct(
                    id=pid,
                    vector=vectors_by_id[pid],
                    payload=payload,
                )
            )

        if not points:
            raise QdrantStoreError(
                "qdrant_chunks_missing",
                "No hay chunks en DB alineados con los vectores a indexar.",
            )

        batch = settings.qdrant_upsert_batch_size
        collection = settings.qdrant_collection
        for offset in range(0, len(points), batch):
            client.upsert(
                collection_name=collection,
                points=points[offset : offset + batch],
            )

        return {
            "qdrant_status": "done",
            "qdrant_upsert_count": len(points),
            "qdrant_collection": collection,
            "qdrant_vector_size": vector_size,
        }

    return _wrap_qdrant_errors(_run, code="qdrant_upsert_failed")


def delete_document_vectors(
    settings: Settings,
    *,
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
) -> int:
    """Borra puntos por filtro doc_id (+ kb_id). Consistente con soft delete en Postgres."""
    if not settings.qdrant_enabled:
        return 0

    def _run() -> int:
        client = get_qdrant_client(settings)
        collection = settings.qdrant_collection
        if not client.collection_exists(collection):
            return 0

        result = client.delete(
            collection_name=collection,
            points_selector=Filter(
                must=[
                    FieldCondition(key="kb_id", match=MatchValue(value=str(kb_id))),
                    FieldCondition(key="doc_id", match=MatchValue(value=str(doc_id))),
                ]
            ),
        )
        deleted = getattr(result, "status", None)
        logger.info(
            "Qdrant delete doc_id=%s kb_id=%s collection=%s status=%s",
            doc_id,
            kb_id,
            collection,
            deleted,
        )
        return 1

    return _wrap_qdrant_errors(_run, code="qdrant_delete_failed")


def search_chunks(
    settings: Settings,
    *,
    query_vector: list[float],
    kb_id: uuid.UUID,
    limit: int = 10,
    doc_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    """Búsqueda vectorial con filtro server-side por kb_id (y opcional doc_id)."""
    if not settings.qdrant_enabled:
        return []

    def _run() -> list[dict[str, Any]]:
        client = get_qdrant_client(settings)
        collection = settings.qdrant_collection
        if not client.collection_exists(collection):
            return []

        must: list[FieldCondition] = [
            FieldCondition(key="kb_id", match=MatchValue(value=str(kb_id))),
        ]
        if doc_id is not None:
            must.append(FieldCondition(key="doc_id", match=MatchValue(value=str(doc_id))))

        hits = vector_search(
            client,
            collection_name=collection,
            query_vector=query_vector,
            query_filter=Filter(must=must),
            limit=limit,
        )
        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "payload": hit.payload or {},
            }
            for hit in hits
        ]

    return _wrap_qdrant_errors(_run, code="qdrant_search_failed")
