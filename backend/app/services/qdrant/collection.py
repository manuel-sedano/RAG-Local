"""Creación y validación de la colección `rag_chunks_v1`."""

from __future__ import annotations

import logging

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.core.config import Settings
from app.services.qdrant.errors import QdrantStoreError

logger = logging.getLogger(__name__)


def _collection_vector_size(info) -> int:
    vectors = info.config.params.vectors
    if hasattr(vectors, "size"):
        return int(vectors.size)
    if isinstance(vectors, dict) and vectors:
        first = next(iter(vectors.values()))
        return int(first.size)
    raise QdrantStoreError(
        "qdrant_unknown_config",
        "No se pudo leer la dimensión de vectores de la colección.",
    )


def ensure_collection(client: QdrantClient, settings: Settings, vector_size: int) -> None:
    """Asegura colección global con distancia cosine y dimensión del modelo."""
    if vector_size < 1:
        raise QdrantStoreError("qdrant_invalid_vector_size", "Dimensión de vector inválida.")

    name = settings.qdrant_collection
    if client.collection_exists(name):
        info = client.get_collection(name)
        existing_size = _collection_vector_size(info)
        if existing_size != vector_size:
            raise QdrantStoreError(
                "qdrant_dimension_mismatch",
                (
                    f"La colección {name} tiene dimensión {existing_size}, "
                    f"pero el modelo actual produce {vector_size}."
                ),
            )
        return

    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )
    logger.info("Colección Qdrant creada: %s (size=%s, distance=cosine)", name, vector_size)
