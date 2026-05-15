"""Tests del servicio de embeddings (fake en test; sin descargar bge-m3)."""

from __future__ import annotations

import uuid

import pytest

from app.core.config import Settings, clear_settings_cache
from app.services.embeddings.errors import EmbeddingError
from app.services.embeddings.fake import embed_texts_fake
from app.services.embeddings.service import embed_texts, stable_qdrant_point_id, vector_l2_norm


def _test_settings(**overrides: object) -> Settings:
    clear_settings_cache()
    base: dict[str, object] = {
        "environment": "test",
        "embedding_backend": "fake",
        "embedding_fake_dimension": 32,
        "embedding_normalize": True,
        "embedding_batch_size": 16,
        "embedding_batch_size_min": 4,
    }
    base.update(overrides)
    return Settings(**base)


def test_embed_texts_deterministic_for_fixed_text() -> None:
    settings = _test_settings()
    text = "Texto fijo con acentos: política, año, niño."
    a = embed_texts([text, text], settings)
    b = embed_texts([text, text], settings)
    assert a == b
    assert len(a) == 2
    assert a[0] == a[1]


def test_embed_texts_normalized_unit_length() -> None:
    settings = _test_settings(embedding_normalize=True)
    vectors = embed_texts(["hola mundo"], settings)
    norm = vector_l2_norm(vectors[0])
    assert abs(norm - 1.0) < 1e-5


def test_embed_texts_batching_produces_one_vector_per_input() -> None:
    settings = _test_settings(embedding_batch_size=8)
    texts = [f"fragmento número {i} con contenido" for i in range(37)]
    vectors = embed_texts(texts, settings)
    assert len(vectors) == len(texts)
    assert all(len(v) == settings.embedding_fake_dimension for v in vectors)


def test_stable_qdrant_point_id_matches_chunk_uuid() -> None:
    chunk_id = uuid.uuid4()
    assert stable_qdrant_point_id(chunk_id) == str(chunk_id)


def test_fake_embed_direct_batch_sizes() -> None:
    settings = _test_settings()
    batch_a = embed_texts_fake(["a", "b"], settings)
    batch_b = embed_texts_fake(["c"], settings)
    assert len(batch_a) == 2
    assert len(batch_b) == 1


def test_sentence_transformer_backend_requires_dependency() -> None:
    settings = _test_settings(embedding_backend="sentence_transformers")
    assert settings.resolved_embedding_backend() == "sentence_transformers"
    with pytest.raises(EmbeddingError, match="embedding_dependency_missing|sentence"):
        embed_texts(["hola"], settings)
