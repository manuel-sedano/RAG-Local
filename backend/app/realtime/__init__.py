"""Socket.IO: namespace /chat, auth JWT y emisión de eventos."""

from app.realtime.emitters import emit_ingest_progress
from app.realtime.server import create_socketio_server, get_socketio_server

__all__ = [
    "create_socketio_server",
    "get_socketio_server",
    "emit_ingest_progress",
]
