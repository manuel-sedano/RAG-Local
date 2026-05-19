"""Búsqueda híbrida de chunks por KB (debug / RAG)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_kb_access
from app.core.config import get_settings
from app.services.retrieval import SearchFilters, hybrid_search

router = APIRouter(prefix="/kbs", tags=["search"])


class SearchFiltersBody(BaseModel):
    tags: list[str] = Field(default_factory=list)
    mime_types: list[str] = Field(default_factory=list)
    source: str | None = None


class KbSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4096)
    top_k: int | None = Field(default=None, ge=1, le=100)
    hybrid: bool | None = Field(
        default=None,
        description="Si null, usa RAG_HYBRID_ENABLED del entorno.",
    )
    filters: SearchFiltersBody | None = None


class KbSearchItem(BaseModel):
    chunk_id: uuid.UUID
    doc_id: uuid.UUID
    score: float
    page: int | None = None
    snippet: str
    vector_score: float | None = None
    bm25_score: float | None = None


class KbSearchResponse(BaseModel):
    items: list[KbSearchItem]


@router.post("/{kb_id}/search", response_model=KbSearchResponse)
def post_kb_search(
    kb_id: Annotated[uuid.UUID, Depends(require_kb_access("viewer"))],
    db: Annotated[Session, Depends(get_db)],
    body: KbSearchRequest,
) -> KbSearchResponse:
    settings = get_settings()
    filters = None
    if body.filters is not None:
        filters = SearchFilters(
            tags=body.filters.tags,
            mime_types=body.filters.mime_types,
            source=body.filters.source,
        )
    effective_top_k = body.top_k if body.top_k is not None else min(20, settings.rag_search_max_top_k)
    try:
        hits = hybrid_search(
            db,
            settings,
            kb_id=kb_id,
            query=body.query,
            top_k=effective_top_k,
            filters=filters,
            hybrid=body.hybrid,
        )
    except ValueError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "VALIDATION_ERROR",
                "message": str(e),
                "details": {},
            },
        ) from e

    return KbSearchResponse(
        items=[
            KbSearchItem(
                chunk_id=h.chunk_id,
                doc_id=h.doc_id,
                score=h.score,
                page=h.page,
                snippet=h.snippet,
                vector_score=h.vector_score,
                bm25_score=h.bm25_score,
            )
            for h in hits
        ]
    )
