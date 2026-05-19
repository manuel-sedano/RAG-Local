"""Tests unitarios de retrieval (BM25, RRF, filtros) sin servicios externos."""

from __future__ import annotations

import uuid

import pytest

from app.core.config import Settings, clear_settings_cache
from app.services.retrieval.bm25_index import (
    bm25_search,
    clear_all_indexes,
    tokenize,
)
from app.services.retrieval.filters import matches_filters
from app.services.retrieval.fusion import reciprocal_rank_fusion
from app.services.retrieval.types import ChunkCandidate, SearchFilters


def _settings(**overrides: object) -> Settings:
    clear_settings_cache()
    base: dict[str, object] = {
        "environment": "test",
        "rag_hybrid_enabled": True,
        "rag_vector_top_k": 50,
        "rag_bm25_top_k": 50,
        "rag_rrf_k": 60,
    }
    base.update(overrides)
    return Settings(**base)


@pytest.fixture(autouse=True)
def _clear_bm25_registry() -> None:
    clear_all_indexes()
    yield
    clear_all_indexes()


def test_tokenize_preserves_accents_and_hyphen_codes() -> None:
    tokens = tokenize("Política de viáticos NOM-035")
    assert "política" in tokens
    assert "nom-035" in tokens
    assert "nom" in tokens
    assert "035" in tokens


def test_rrf_boosts_items_in_both_lists() -> None:
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    fused = reciprocal_rank_fusion([[a, b], [b, c]], rrf_k=60)
    assert fused[b] > fused[a]
    assert fused[b] > fused[c]


def test_matches_filters_tags_any() -> None:
    cand = ChunkCandidate(
        chunk_id=uuid.uuid4(),
        doc_id=uuid.uuid4(),
        kb_id=uuid.uuid4(),
        text="x",
        page_start=1,
        page_end=1,
        mime_type="application/pdf",
        tags=["finanzas", "viaticos"],
        source="manual.pdf",
    )
    assert matches_filters(cand, SearchFilters(tags=["viaticos"]))
    assert not matches_filters(cand, SearchFilters(tags=["legal"]))


def test_bm25_favors_exact_proper_noun() -> None:
    """NOM-035 debe rankear mejor con BM25 que un texto genérico semánticamente cercano."""
    from rank_bm25 import BM25Okapi

    from app.services.retrieval.bm25_index import _get_or_create_index

    settings = _settings()
    kb_id = uuid.uuid4()
    doc_nom = uuid.uuid4()
    doc_gen = uuid.uuid4()
    chunk_nom = uuid.uuid4()
    chunk_gen = uuid.uuid4()

    idx = _get_or_create_index(kb_id)
    idx.candidates[chunk_nom] = ChunkCandidate(
        chunk_id=chunk_nom,
        doc_id=doc_nom,
        kb_id=kb_id,
        text="La norma oficial mexicana NOM-035-STPS-2018 regula factores de riesgo psicosocial.",
        page_start=1,
        page_end=1,
        mime_type="application/pdf",
        tags=["normativa"],
        source="nom.pdf",
    )
    idx.candidates[chunk_gen] = ChunkCandidate(
        chunk_id=chunk_gen,
        doc_id=doc_gen,
        kb_id=kb_id,
        text="Los empleados deben cuidar su salud mental y el ambiente laboral en general.",
        page_start=1,
        page_end=1,
        mime_type="application/pdf",
        tags=["general"],
        source="general.pdf",
    )
    idx.corpus_ids = [chunk_nom, chunk_gen]
    idx.tokenized_corpus = [tokenize(idx.candidates[chunk_nom].text), tokenize(idx.candidates[chunk_gen].text)]
    idx.bm25 = BM25Okapi(idx.tokenized_corpus)

    hits = bm25_search(kb_id, "NOM-035", top_k=5, settings=settings)
    assert hits
    assert hits[0][0].doc_id == doc_nom
