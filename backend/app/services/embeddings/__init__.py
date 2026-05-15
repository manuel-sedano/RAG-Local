"""Embeddings de chunks (bge-m3 / fake para tests)."""

from app.services.embeddings.service import (
    EmbeddingError,
    embed_texts,
    embed_document_chunks,
)

__all__ = [
    "EmbeddingError",
    "embed_texts",
    "embed_document_chunks",
]
