"""Orquestación de retrieval híbrido (vector + BM25 + RRF)."""

from __future__ import annotations

import logging
import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.document import Chunk, Document
from app.services.embeddings import embed_texts
from app.services.qdrant import search_chunks
from app.services.retrieval.bm25_index import bm25_search, refresh_kb_bm25_index
from app.services.retrieval.filters import candidate_from_payload, enrich_candidate_from_db, matches_filters
from app.services.retrieval.fusion import log_fusion_debug, reciprocal_rank_fusion
from app.services.retrieval.rerank import rerank_search_hits
from app.services.retrieval.types import ChunkCandidate, SearchFilters, SearchHit, SearchResult

logger = logging.getLogger(__name__)

_QUERY_MIN_LEN = 2
_QUERY_MAX_LEN = 4096
_STRIP_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def normalize_query(query: str) -> str:
    s = _STRIP_RE.sub("", query).strip()
    if len(s) < _QUERY_MIN_LEN:
        msg = "La consulta es demasiado corta."
        raise ValueError(msg)
    if len(s) > _QUERY_MAX_LEN:
        s = s[:_QUERY_MAX_LEN]
    return s


def _snippet(text: str, settings: Settings) -> str:
    max_chars = settings.qdrant_snippet_max_chars or 500
    if max_chars <= 0:
        return ""
    return text[:max_chars]


def _page_display(candidate: ChunkCandidate) -> int | None:
    if candidate.page_start is not None:
        return candidate.page_start
    return candidate.page_end


def _load_candidates_from_db(
    session: Session,
    chunk_ids: list[uuid.UUID],
) -> dict[uuid.UUID, ChunkCandidate]:
    if not chunk_ids:
        return {}
    rows = session.execute(
        select(Chunk, Document)
        .join(Document, Chunk.document_id == Document.id)
        .where(Chunk.id.in_(chunk_ids))
    ).all()
    out: dict[uuid.UUID, ChunkCandidate] = {}
    for chunk, doc in rows:
        if doc.deleted_at is not None or doc.status != "READY":
            continue
        out[chunk.id] = ChunkCandidate(
            chunk_id=chunk.id,
            doc_id=doc.id,
            kb_id=chunk.kb_id,
            text=chunk.text,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            mime_type=doc.mime_type,
            tags=[],
            source=doc.source,
        )
        enrich_candidate_from_db(
            out[chunk.id],
            text=chunk.text,
            tags=doc.tags,
            source=doc.source,
            mime_type=doc.mime_type,
        )
    return out


def _vector_candidates(
    session: Session,
    settings: Settings,
    *,
    kb_id: uuid.UUID,
    query: str,
    limit: int,
    filters: SearchFilters | None,
) -> list[tuple[ChunkCandidate, float]]:
    if not settings.qdrant_enabled:
        return []

    vectors = embed_texts([query], settings)
    if not vectors:
        return []

    hits = search_chunks(
        settings,
        query_vector=vectors[0],
        kb_id=kb_id,
        limit=limit,
    )

    chunk_ids: list[uuid.UUID] = []
    scores_by_id: dict[uuid.UUID, float] = {}
    for hit in hits:
        payload = hit.get("payload") or {}
        cand = candidate_from_payload(payload, snippet_max=settings.qdrant_snippet_max_chars)
        if cand is None:
            try:
                cid = uuid.UUID(str(hit["id"]))
            except (KeyError, ValueError, TypeError):
                continue
            chunk_ids.append(cid)
            scores_by_id[cid] = float(hit.get("score") or 0.0)
            continue
        if cand.kb_id != kb_id:
            continue
        chunk_ids.append(cand.chunk_id)
        scores_by_id[cand.chunk_id] = float(hit.get("score") or 0.0)

    db_map = _load_candidates_from_db(session, chunk_ids)
    out: list[tuple[ChunkCandidate, float]] = []
    for cid in chunk_ids:
        score = scores_by_id.get(cid, 0.0)
        cand = db_map.get(cid)
        if cand is None:
            continue
        cand.vector_score = score
        if matches_filters(cand, filters):
            out.append((cand, score))
    return out


def hybrid_search(
    session: Session,
    settings: Settings,
    *,
    kb_id: uuid.UUID,
    query: str,
    top_k: int | None = None,
    filters: SearchFilters | None = None,
    hybrid: bool | None = None,
    rerank: bool | None = None,
) -> SearchResult:
    """Ejecuta retrieval híbrido, rerank opcional (FlashRank) y devuelve hits + métricas."""
    q = normalize_query(query)
    use_hybrid = settings.rag_hybrid_enabled if hybrid is None else hybrid
    use_rerank = settings.rag_rerank_enabled if rerank is None else rerank
    final_limit = top_k if top_k is not None else settings.rag_rerank_top_k
    final_limit = min(max(1, final_limit), settings.rag_search_max_top_k)
    candidate_limit = (
        settings.rag_rerank_candidate_top_k if use_rerank else final_limit
    )

    vector_top_k = settings.rag_vector_top_k
    bm25_top_k = settings.rag_bm25_top_k if use_hybrid else 0

    vector_ranked: list[tuple[ChunkCandidate, float]] = []
    bm25_ranked: list[tuple[ChunkCandidate, float]] = []

    try:
        vector_ranked = _vector_candidates(
            session,
            settings,
            kb_id=kb_id,
            query=q,
            limit=vector_top_k,
            filters=filters,
        )
    except Exception:
        logger.exception("Fallo en búsqueda vectorial kb_id=%s", kb_id)
        vector_ranked = []

    if use_hybrid and bm25_top_k > 0:
        try:
            bm25_ranked = bm25_search(kb_id, q, top_k=bm25_top_k, settings=settings)
            if not bm25_ranked:
                refresh_kb_bm25_index(session, kb_id, settings)
                bm25_ranked = bm25_search(kb_id, q, top_k=bm25_top_k, settings=settings)
        except Exception:
            logger.exception("Fallo en búsqueda BM25 kb_id=%s", kb_id)
            bm25_ranked = []

    vector_ids = [c.chunk_id for c, _ in vector_ranked]
    bm25_ids = [c.chunk_id for c, _ in bm25_ranked]

    if use_hybrid and vector_ids and bm25_ids:
        fused_scores = reciprocal_rank_fusion(
            [vector_ids, bm25_ids],
            rrf_k=settings.rag_rrf_k,
        )
        log_fusion_debug(
            query=q,
            kb_id=kb_id,
            vector_ranks=vector_ids,
            bm25_ranks=bm25_ids,
            fused=fused_scores,
        )
        by_id: dict[uuid.UUID, ChunkCandidate] = {}
        for cand, score in vector_ranked:
            cand.vector_score = score
            by_id[cand.chunk_id] = cand
        for cand, score in bm25_ranked:
            cand.bm25_score = score
            existing = by_id.get(cand.chunk_id)
            if existing:
                existing.bm25_score = score
                if not existing.text:
                    existing.text = cand.text
            else:
                if matches_filters(cand, filters):
                    by_id[cand.chunk_id] = cand

        ranked_ids = sorted(
            by_id.keys(),
            key=lambda cid: fused_scores.get(cid, 0.0),
            reverse=True,
        )[:candidate_limit]
        hits = _hits_from_candidates(by_id, ranked_ids, fused_scores, settings)
    elif vector_ranked:
        hits = _hits_from_scored(vector_ranked[:candidate_limit], settings)
    elif bm25_ranked:
        filtered = [(c, s) for c, s in bm25_ranked if matches_filters(c, filters)]
        hits = _hits_from_scored(filtered[:candidate_limit], settings)
    else:
        return SearchResult(hits=[])

    return _apply_rerank(q, hits, settings, use_rerank=use_rerank, final_limit=final_limit)


def _hits_from_candidates(
    by_id: dict[uuid.UUID, ChunkCandidate],
    ranked_ids: list[uuid.UUID],
    scores_by_id: dict[uuid.UUID, float],
    settings: Settings,
) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for cid in ranked_ids:
        cand = by_id[cid]
        score = round(scores_by_id.get(cid, 0.0), 6)
        hits.append(
            SearchHit(
                chunk_id=cand.chunk_id,
                doc_id=cand.doc_id,
                score=score,
                page=_page_display(cand),
                snippet=_snippet(cand.text, settings),
                vector_score=cand.vector_score,
                bm25_score=cand.bm25_score,
                retrieval_score=score,
            )
        )
    return hits


def _hits_from_scored(
    source: list[tuple[ChunkCandidate, float]],
    settings: Settings,
) -> list[SearchHit]:
    return [
        SearchHit(
            chunk_id=cand.chunk_id,
            doc_id=cand.doc_id,
            score=round(score, 6),
            page=_page_display(cand),
            snippet=_snippet(cand.text, settings),
            vector_score=cand.vector_score,
            bm25_score=cand.bm25_score if cand.bm25_score is not None else score,
            retrieval_score=round(score, 6),
        )
        for cand, score in source
    ]


def _apply_rerank(
    query: str,
    hits: list[SearchHit],
    settings: Settings,
    *,
    use_rerank: bool,
    final_limit: int,
) -> SearchResult:
    if not hits:
        return SearchResult(hits=[])

    for hit in hits:
        if hit.retrieval_score is None:
            hit.retrieval_score = hit.score

    if not use_rerank:
        return SearchResult(hits=hits[:final_limit])

    reranked, metrics = rerank_search_hits(query, hits, settings, top_k=final_limit)
    logger.debug(
        "Rerank kb query=%r status=%s ms=%s in=%s out=%s backend=%s",
        query[:80],
        metrics.status,
        metrics.latency_ms,
        metrics.input_count,
        metrics.output_count,
        metrics.backend,
    )
    return SearchResult(
        hits=reranked,
        rerank_status=metrics.status,
        rerank_latency_ms=metrics.latency_ms,
        rerank_backend=metrics.backend,
    )
