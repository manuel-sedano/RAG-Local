"""Emisión de eventos Socket.IO (chat e ingesta)."""

from __future__ import annotations

import uuid
from typing import Any

import socketio

CHAT_NAMESPACE = "/chat"


def chat_room(chat_id: uuid.UUID | str) -> str:
    return f"chat:{chat_id}"


def ingest_room(document_id: uuid.UUID | str) -> str:
    return f"ingest:{document_id}"


async def emit_chat_token(
    sio: socketio.AsyncServer,
    *,
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
    token: str,
) -> None:
    await sio.emit(
        "chat:token",
        {
            "chat_id": str(chat_id),
            "message_id": str(message_id),
            "token": token,
        },
        room=chat_room(chat_id),
        namespace=CHAT_NAMESPACE,
    )


async def emit_chat_citation(
    sio: socketio.AsyncServer,
    *,
    message_id: uuid.UUID,
    citations: list[dict[str, Any]],
    chat_id: uuid.UUID | None = None,
) -> None:
    payload: dict[str, Any] = {
        "message_id": str(message_id),
        "citations": citations,
    }
    if chat_id is not None:
        payload["chat_id"] = str(chat_id)
    room = chat_room(chat_id) if chat_id else None
    await sio.emit(
        "chat:citation",
        payload,
        room=room,
        namespace=CHAT_NAMESPACE,
    )


async def emit_chat_done(
    sio: socketio.AsyncServer,
    *,
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
    status: str = "DONE",
    error: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "chat_id": str(chat_id),
        "message_id": str(message_id),
        "status": status,
    }
    if error:
        payload["error"] = error[:500]
    await sio.emit(
        "chat:done",
        payload,
        room=chat_room(chat_id),
        namespace=CHAT_NAMESPACE,
    )


async def emit_ingest_progress(
    sio: socketio.AsyncServer,
    *,
    document_id: uuid.UUID,
    stage: str,
    percent: int,
    kb_id: uuid.UUID | None = None,
) -> None:
    payload: dict[str, Any] = {
        "document_id": str(document_id),
        "stage": stage,
        "percent": max(0, min(100, percent)),
    }
    if kb_id is not None:
        payload["kb_id"] = str(kb_id)
    await sio.emit(
        "ingest:progress",
        payload,
        room=ingest_room(document_id),
        namespace=CHAT_NAMESPACE,
    )
