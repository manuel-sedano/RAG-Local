"""Validación de configuración (settings) por entorno."""

from __future__ import annotations

import pytest

from app.core.config import Settings, clear_settings_cache


def test_test_environment_allows_short_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("JWT_SECRET", "")
    clear_settings_cache()
    s = Settings()
    assert s.environment == "test"
    assert len(s.jwt_secret) >= 16


def test_local_requires_jwt_min_length(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("JWT_SECRET", "short")
    clear_settings_cache()
    with pytest.raises(ValueError):
        Settings()


def test_staging_requires_long_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("JWT_SECRET", "x" * 31)
    clear_settings_cache()
    with pytest.raises(ValueError):
        Settings()


def test_rag_retrieval_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    clear_settings_cache()
    s = Settings()
    assert s.rag_hybrid_enabled is True
    assert s.rag_vector_top_k == 50
    assert s.rag_bm25_top_k == 50
    assert s.rag_rrf_k == 60
    assert s.rag_rerank_enabled is True
    assert s.rag_rerank_candidate_top_k == 30
    assert s.rag_rerank_top_k == 10
    assert s.resolved_rerank_backend() == "fake"


def test_database_url_must_be_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp.db")
    clear_settings_cache()
    with pytest.raises(ValueError):
        Settings()


def test_chunk_overlap_must_be_less_than_chunk_size(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("CHUNK_SIZE_TOKENS", "100")
    monkeypatch.setenv("CHUNK_OVERLAP_TOKENS", "100")
    clear_settings_cache()
    with pytest.raises(ValueError, match="CHUNK_OVERLAP"):
        Settings()
