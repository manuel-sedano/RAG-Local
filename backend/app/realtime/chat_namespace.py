"""Handlers Socket.IO namespace /chat."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import socketio

from app.api.deps import ensure_kb_access
from app.models.chat import Chat
from app.models.user import User
from app.realtime.auth import SocketAuthError, authenticate_socket_connection
from app.realtime.emitters import CHAT_NAMESPACE, chat_room, ingest_room

logger = logging.getLogger(__name__)


def register_chat_namespace(sio: socketio.AsyncServer) -> None:
    @sio.on("connect", namespace=CHAT_NAMESPACE)
    async def connect(sid: str, environ: dict[str, Any], auth: dict[str, Any] | None) -> bool:
        try:
            user = authenticate_socket_connection(environ, auth)
        except SocketAuthError as e:
            logger.info("Socket connect rechazado sid=%s: %s", sid, e)
            return False
        await sio.save_session(sid, {"user_id": str(user.id)}, namespace=CHAT_NAMESPACE)
        return True

    @sio.on("disconnect", namespace=CHAT_NAMESPACE)
    async def disconnect(sid: str) -> None:
        _ = sid

    @sio.on("chat:join", namespace=CHAT_NAMESPACE)
    async def chat_join(sid: str, data: dict[str, Any] | None) -> dict[str, Any]:
        session_data = await sio.get_session(sid, namespace=CHAT_NAMESPACE)
        user_id = uuid.UUID(session_data["user_id"])
        if not data or "chat_id" not in data:
            return {"ok": False, "error": "Falta chat_id."}
        try:
            chat_id = uuid.UUID(str(data["chat_id"]))
        except ValueError:
            return {"ok": False, "error": "chat_id inválido."}

        from app.db.session import get_session_factory

        factory = get_session_factory()
        with factory() as db:
            chat = db.get(Chat, chat_id)
            if chat is None or chat.deleted_at is not None:
                return {"ok": False, "error": "Chat no encontrado."}
            user = db.get(User, user_id)
            if user is None:
                return {"ok": False, "error": "Usuario no válido."}
            try:
                ensure_kb_access(chat.kb_id, user, db, min_role="viewer")
            except Exception:
                return {"ok": False, "error": "Sin acceso a la KB del chat."}

        await sio.enter_room(sid, chat_room(chat_id), namespace=CHAT_NAMESPACE)
        return {"ok": True, "room": chat_room(chat_id)}

    @sio.on("ingest:join", namespace=CHAT_NAMESPACE)
    async def ingest_join(sid: str, data: dict[str, Any] | None) -> dict[str, Any]:
        session_data = await sio.get_session(sid, namespace=CHAT_NAMESPACE)
        _ = uuid.UUID(session_data["user_id"])
        if not data or "document_id" not in data:
            return {"ok": False, "error": "Falta document_id."}
        try:
            doc_id = uuid.UUID(str(data["document_id"]))
        except ValueError:
            return {"ok": False, "error": "document_id inválido."}

        await sio.enter_room(sid, ingest_room(doc_id), namespace=CHAT_NAMESPACE)
        return {"ok": True, "room": ingest_room(doc_id)}
