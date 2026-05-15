"""Cliente Qdrant compartido (HTTP)."""

from __future__ import annotations

import os

from qdrant_client import QdrantClient

from app.core.config import Settings


def _build_client(**kwargs: object) -> QdrantClient:
    """Instancia QdrantClient; `check_compatibility` solo en clientes recientes."""
    base = dict(kwargs)
    try:
        return QdrantClient(**base, check_compatibility=False)
    except TypeError:
        return QdrantClient(**base)


def get_qdrant_client(settings: Settings) -> QdrantClient:
    """URL explícita en TEST_QDRANT_URL; si no, host/puerto de settings."""
    common = {
        "timeout": settings.qdrant_timeout_seconds,
        "prefer_grpc": False,
    }
    test_url = os.environ.get("TEST_QDRANT_URL", "").strip()
    if test_url:
        return _build_client(url=test_url, **common)
    return _build_client(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        **common,
    )
