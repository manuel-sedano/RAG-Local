"""Extrae kb_id / chat_id / document_id de rutas API para correlación en logs."""

from __future__ import annotations

import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.log_context import log_context

_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
_KB_RE = re.compile(rf"^/api/kbs/(?P<kb_id>{_UUID})", re.IGNORECASE)
_CHAT_RE = re.compile(rf"/chats/(?P<chat_id>{_UUID})", re.IGNORECASE)
_DOC_RE = re.compile(rf"/documents/(?P<doc_id>{_UUID})", re.IGNORECASE)


def _ids_from_path(path: str) -> dict[str, str]:
    out: dict[str, str] = {}
    kb = _KB_RE.search(path)
    if kb:
        out["kb_id"] = kb.group("kb_id")
    chat = _CHAT_RE.search(path)
    if chat:
        out["chat_id"] = chat.group("chat_id")
    doc = _DOC_RE.search(path)
    if doc:
        out["document_id"] = doc.group("doc_id")
    return out


class CorrelationPathMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        ids = _ids_from_path(request.url.path)
        with log_context(
            kb_id=ids.get("kb_id"),
            chat_id=ids.get("chat_id"),
            document_id=ids.get("document_id"),
        ):
            return await call_next(request)
