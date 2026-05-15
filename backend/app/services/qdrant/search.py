"""Búsqueda vectorial compatible con qdrant-client 1.12 (`search`) y 1.16+ (`query_points`)."""

from __future__ import annotations

from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Filter


def vector_search(
    client: QdrantClient,
    *,
    collection_name: str,
    query_vector: list[float],
    query_filter: Filter,
    limit: int,
) -> list[Any]:
    """Devuelve puntos puntuados (ScoredPoint) de la colección."""
    if hasattr(client, "query_points"):
        response = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        return list(response.points)

    return client.search(
        collection_name=collection_name,
        query_vector=query_vector,
        query_filter=query_filter,
        limit=limit,
        with_payload=True,
    )
