"""Embeddings con Sentence Transformers (bge-m3)."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from functools import lru_cache

from app.core.config import Settings
from app.services.embeddings.errors import EmbeddingError, RecoverableEmbeddingError

logger = logging.getLogger(__name__)


@lru_cache(maxsize=2)
def _load_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        msg = (
            "sentence-transformers no está instalado. "
            "Instala con: pip install -e '.[embeddings]'"
        )
        raise EmbeddingError("embedding_dependency_missing", msg) from e
    return SentenceTransformer(model_name)


def _encode_batch(model, texts: list[str], settings: Settings) -> list[list[float]]:
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            model.encode,
            texts,
            batch_size=len(texts),
            normalize_embeddings=settings.embedding_normalize,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        try:
            arr = future.result(timeout=settings.embedding_timeout_seconds)
        except FuturesTimeoutError as e:
            raise RecoverableEmbeddingError(
                "embedding_timeout",
                f"Embeddings superaron {settings.embedding_timeout_seconds}s.",
            ) from e
    return [row.tolist() for row in arr]


def embed_texts_sentence_transformer(
    texts: list[str],
    settings: Settings,
    *,
    batch_size: int,
) -> list[list[float]]:
    if not texts:
        return []
    model = _load_model(settings.embedding_model_name)
    out: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        try:
            out.extend(_encode_batch(model, batch, settings))
        except MemoryError as e:
            raise RecoverableEmbeddingError("embedding_oom", str(e)) from e
        except RuntimeError as e:
            if "out of memory" in str(e).lower() or "cuda" in str(e).lower():
                raise RecoverableEmbeddingError("embedding_oom", str(e)) from e
            raise EmbeddingError("embedding_runtime_error", str(e)) from e
    return out
