"""Errores del almacén vectorial Qdrant."""

from __future__ import annotations


class QdrantStoreError(Exception):
    """Error estable para propagar a ingesta o API."""

    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        self.message = message or code
        super().__init__(self.message)
