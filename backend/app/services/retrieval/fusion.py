"""Fusión de rankings (RRF)."""

from __future__ import annotations

import logging
import uuid

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    ranked_lists: list[list[uuid.UUID]],
    *,
    rrf_k: int,
) -> dict[uuid.UUID, float]:
    """Combina listas ordenadas con Reciprocal Rank Fusion."""
    scores: dict[uuid.UUID, float] = {}
    for ranked in ranked_lists:
        for rank, chunk_id in enumerate(ranked, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
    return scores


def log_fusion_debug(
    *,
    query: str,
    kb_id: uuid.UUID,
    vector_ranks: list[uuid.UUID],
    bm25_ranks: list[uuid.UUID],
    fused: dict[uuid.UUID, float],
    top_n: int = 5,
) -> None:
    if not logger.isEnabledFor(logging.DEBUG):
        return
    top = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:top_n]
    logger.debug(
        "RRF fusion kb_id=%s query=%r vector_candidates=%s bm25_candidates=%s top=%s",
        kb_id,
        query[:120],
        len(vector_ranks),
        len(bm25_ranks),
        [(str(cid), round(score, 6)) for cid, score in top],
    )
