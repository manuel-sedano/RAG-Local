"""Instancia global de Socket.IO (ASGI)."""

from __future__ import annotations

import socketio

from app.core.config import Settings
from app.realtime.chat_namespace import register_chat_namespace

_sio: socketio.AsyncServer | None = None


def create_socketio_server(settings: Settings) -> socketio.AsyncServer:
    global _sio
    sio = socketio.AsyncServer(
        async_mode="asgi",
        cors_allowed_origins=settings.socketio_cors_origin_list or "*",
        logger=False,
        engineio_logger=False,
    )
    register_chat_namespace(sio)
    _sio = sio
    return sio


def get_socketio_server() -> socketio.AsyncServer | None:
    return _sio
