"""Reranking de candidatos con FlashRank (o fake en tests)."""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass

from app.core.config import Settings
from app.observability.metrics import observe_retrieval
from app.services.retrieval.types import SearchHit

logger = logging.getLogger(__name__)

_ranker_lock = threading.Lock()
_ranker_instance = None
_ranker_model_key: str | None = None

_TOKEN_SPLIT = re.compile(r"\W+", re.UNICODE)


@dataclass
class RerankMetrics:
    status: str
    latency_ms: float
    input_count: int
    output_count: int
    backend: str


def _truncate(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[:max_chars]


def _fake_rerank_scores(query: str, hits: list[SearchHit]) -> list[tuple[SearchHit, float]]:
    """Rerank determinista por solapamiento léxico (sin FlashRank)."""
    q_tokens = {t for t in _TOKEN_SPLIT.split(query.lower()) if len(t) >= 2}
    scored: list[tuple[SearchHit, float]] = []
    for hit in hits:
        text_tokens = {t for t in _TOKEN_SPLIT.split(hit.snippet.lower()) if len(t) >= 2}
        overlap = len(q_tokens & text_tokens) if q_tokens else 0
        fake_score = overlap * 10.0 + hit.score
        scored.append((hit, fake_score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def _get_flashrank_ranker(settings: Settings):
    global _ranker_instance, _ranker_model_key
    key = f"{settings.rag_rerank_model_name}:{settings.rag_rerank_max_length}:{settings.rag_rerank_cache_dir}"
    with _ranker_lock:
        if _ranker_instance is not None and _ranker_model_key == key:
            return _ranker_instance
        try:
            from flashrank import Ranker
        except ImportError as e:
            msg = "FlashRank no instalado. Ejecuta: pip install -e '.[rerank]'"
            raise RuntimeError(msg) from e

        kwargs: dict = {
            "model_name": settings.rag_rerank_model_name,
            "max_length": settings.rag_rerank_max_length,
        }
        if settings.rag_rerank_cache_dir.strip():
            kwargs["cache_dir"] = settings.rag_rerank_cache_dir.strip()
        _ranker_instance = Ranker(**kwargs)
        _ranker_model_key = key
        return _ranker_instance


def clear_reranker_cache() -> None:
    """Libera el ranker singleton (tests)."""
    global _ranker_instance, _ranker_model_key
    with _ranker_lock:
        _ranker_instance = None
        _ranker_model_key = None


def rerank_search_hits(
    query: str,
    hits: list[SearchHit],
    settings: Settings,
    *,
    top_k: int | None = None,
) -> tuple[list[SearchHit], RerankMetrics]:
    """Reordena hits (top-N → top-M). Si falla o está deshabilitado, devuelve el ranking previo."""
    limit = top_k if top_k is not None else settings.rag_rerank_top_k
    limit = min(max(1, limit), settings.rag_search_max_top_k)

    def _finish(
        out_hits: list[SearchHit],
        metrics: RerankMetrics,
    ) -> tuple[list[SearchHit], RerankMetrics]:
        if settings.prometheus_enabled and metrics.latency_ms > 0:
            observe_retrieval(
                "rerank",
                metrics.latency_ms / 1000.0,
                status=metrics.status,
            )
        return out_hits, metrics

    if not hits:
        return _finish(
            [],
            RerankMetrics(
                status="skipped_empty",
                latency_ms=0.0,
                input_count=0,
                output_count=0,
                backend=settings.resolved_rerank_backend(),
            ),
        )

    if not settings.rag_rerank_enabled or len(hits) <= 1:
        out = hits[:limit]
        return _finish(
            out,
            RerankMetrics(
                status="skipped",
                latency_ms=0.0,
                input_count=len(hits),
                output_count=len(out),
                backend=settings.resolved_rerank_backend(),
            ),
        )

    start = time.perf_counter()
    backend = settings.resolved_rerank_backend()

    try:
        if backend == "fake":
            ranked = _fake_rerank_scores(query, hits)
        else:
            ranked = _flashrank_rerank(query, hits, settings)
        status = "done"
    except Exception:
        logger.exception("Rerank falló; se usa ranking híbrido previo.")
        elapsed = (time.perf_counter() - start) * 1000
        out = hits[:limit]
        return _finish(
            out,
            RerankMetrics(
                status="fallback",
                latency_ms=round(elapsed, 2),
                input_count=len(hits),
                output_count=len(out),
                backend=backend,
            ),
        )

    elapsed = (time.perf_counter() - start) * 1000
    out: list[SearchHit] = []
    for hit, rerank_score in ranked[:limit]:
        hit.rerank_score = round(rerank_score, 6)
        hit.score = hit.rerank_score
        out.append(hit)

    return _finish(
        out,
        RerankMetrics(
            status=status,
            latency_ms=round(elapsed, 2),
            input_count=len(hits),
            output_count=len(out),
            backend=backend,
        ),
    )


def _flashrank_rerank(
    query: str,
    hits: list[SearchHit],
    settings: Settings,
) -> list[tuple[SearchHit, float]]:
    from flashrank import RerankRequest

    ranker = _get_flashrank_ranker(settings)
    max_chars = settings.rag_rerank_max_passage_chars
    passages = [
        {
            "id": str(h.chunk_id),
            "text": _truncate(h.snippet or "", max_chars),
        }
        for h in hits
    ]
    request = RerankRequest(query=query, passages=passages)
    results = ranker.rerank(request)

    by_id = {str(h.chunk_id): h for h in hits}
    ranked: list[tuple[SearchHit, float]] = []
    for row in results:
        cid = str(row.get("id", ""))
        hit = by_id.get(cid)
        if hit is None:
            continue
        ranked.append((hit, float(row.get("score", 0.0))))
    if not ranked:
        return [(h, h.score) for h in hits]
    return ranked
