"""Tests unitarios de reranking (fake backend, sin FlashRank)."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from app.core.config import Settings, clear_settings_cache
from app.services.retrieval.rerank import clear_reranker_cache, rerank_search_hits
from app.services.retrieval.types import SearchHit


def _settings(**overrides: object) -> Settings:
    clear_settings_cache()
    base: dict[str, object] = {
        "environment": "test",
        "rag_rerank_enabled": True,
        "rag_rerank_backend": "fake",
        "rag_rerank_top_k": 5,
    }
    base.update(overrides)
    return Settings(**base)


@pytest.fixture(autouse=True)
def _clear_rerank_singleton() -> None:
    clear_reranker_cache()
    yield
    clear_reranker_cache()


def _hit(snippet: str, score: float = 0.1) -> SearchHit:
    return SearchHit(
        chunk_id=uuid.uuid4(),
        doc_id=uuid.uuid4(),
        score=score,
        page=1,
        snippet=snippet,
        retrieval_score=score,
    )


def test_rerank_few_candidates_does_not_break() -> None:
    settings = _settings()
    hits = [_hit("texto genérico", 0.2)]
    out, metrics = rerank_search_hits("viáticos", hits, settings, top_k=5)
    assert len(out) == 1
    assert metrics.status == "skipped"
    assert metrics.output_count == 1


def test_rerank_fake_reorders_by_lexical_overlap() -> None:
    settings = _settings(rag_rerank_top_k=2)
    h1 = _hit("ambiente laboral general", 0.9)
    h2 = _hit("política de viáticos corporativos", 0.1)
    out, metrics = rerank_search_hits("viáticos", [h1, h2], settings, top_k=2)
    assert metrics.status == "done"
    assert out[0].chunk_id == h2.chunk_id
    assert out[0].rerank_score is not None
    assert out[0].retrieval_score == 0.1


def test_rerank_fallback_on_flashrank_error() -> None:
    settings = _settings(rag_rerank_backend="flashrank")
    hits = [_hit("a", 0.5), _hit("b", 0.4)]

    with patch(
        "app.services.retrieval.rerank._flashrank_rerank",
        side_effect=RuntimeError("flashrank down"),
    ):
        out, metrics = rerank_search_hits("query", hits, settings, top_k=2)

    assert metrics.status == "fallback"
    assert len(out) == 2
    assert out[0].chunk_id == hits[0].chunk_id
