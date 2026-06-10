"""Contexto de correlación para logs (document_id, chat_id, kb_id)."""

from __future__ import annotations

import contextlib
import contextvars
import uuid
from collections.abc import Iterator
from typing import Any

_document_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "document_id",
    default=None,
)
_chat_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "chat_id",
    default=None,
)
_kb_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "kb_id",
    default=None,
)


def _as_id(value: uuid.UUID | str | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def get_document_id() -> str | None:
    return _document_id_ctx.get()


def get_chat_id() -> str | None:
    return _chat_id_ctx.get()


def get_kb_id() -> str | None:
    return _kb_id_ctx.get()


@contextlib.contextmanager
def log_context(
    *,
    document_id: uuid.UUID | str | None = None,
    chat_id: uuid.UUID | str | None = None,
    kb_id: uuid.UUID | str | None = None,
) -> Iterator[None]:
    """Establece IDs de correlación en el contexto actual (async-safe)."""
    tokens: list[tuple[contextvars.ContextVar[str | None], contextvars.Token[str | None]]] = []
    try:
        if document_id is not None:
            tokens.append((_document_id_ctx, _document_id_ctx.set(_as_id(document_id))))
        if chat_id is not None:
            tokens.append((_chat_id_ctx, _chat_id_ctx.set(_as_id(chat_id))))
        if kb_id is not None:
            tokens.append((_kb_id_ctx, _kb_id_ctx.set(_as_id(kb_id))))
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)


def correlation_fields() -> dict[str, Any]:
    """Campos listos para `logger.*(..., extra=correlation_fields())`."""
    out: dict[str, Any] = {}
    if (rid := get_document_id()) is not None:
        out["document_id"] = rid
    if (cid := get_chat_id()) is not None:
        out["chat_id"] = cid
    if (kid := get_kb_id()) is not None:
        out["kb_id"] = kid
    return out
