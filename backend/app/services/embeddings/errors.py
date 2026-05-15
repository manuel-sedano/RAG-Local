"""Errores del servicio de embeddings."""


class EmbeddingError(Exception):
    """Error base de embeddings."""

    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


class RecoverableEmbeddingError(EmbeddingError):
    """Error recuperable (timeout, OOM tras agotar backoff)."""
