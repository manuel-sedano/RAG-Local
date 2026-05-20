"""Autenticación JWT para conexiones Socket.IO."""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import parse_qs

import jwt

from app.core.config import Settings, get_settings
from app.db.session import get_session_factory
from app.models.user import User


class SocketAuthError(Exception):
    """Token inválido o usuario sin acceso."""


def _token_from_environ(environ: dict[str, Any]) -> str | None:
    auth = environ.get("HTTP_AUTHORIZATION") or environ.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    query = environ.get("QUERY_STRING") or ""
    if query:
        params = parse_qs(query)
        tokens = params.get("token") or params.get("access_token")
        if tokens:
            return tokens[0]
    return None


def decode_socket_token(token: str, settings: Settings | None = None) -> dict[str, Any]:
    cfg = settings or get_settings()
    try:
        return jwt.decode(
            token,
            cfg.jwt_secret,
            algorithms=[cfg.jwt_alg],
            options={"require": ["exp", "iat", "sub", "jti"]},
        )
    except jwt.ExpiredSignatureError as e:
        raise SocketAuthError("Token de acceso expirado.") from e
    except jwt.InvalidTokenError as e:
        raise SocketAuthError("Token de acceso inválido.") from e


def authenticate_socket_connection(
    environ: dict[str, Any],
    auth_payload: dict[str, Any] | None,
    *,
    settings: Settings | None = None,
) -> User:
    """Resuelve usuario desde auth payload Socket.IO o query/header."""
    cfg = settings or get_settings()
    token: str | None = None
    if auth_payload and isinstance(auth_payload, dict):
        raw = auth_payload.get("token") or auth_payload.get("access_token")
        if isinstance(raw, str) and raw.strip():
            token = raw.strip()
    if not token:
        token = _token_from_environ(environ)

    if not token:
        raise SocketAuthError("Falta token JWT en auth o query ?token=.")

    payload = decode_socket_token(token, cfg)
    if payload.get("type") not in (None, "access"):
        raise SocketAuthError("Se requiere un token de acceso, no de refresco.")
    try:
        uid = uuid.UUID(str(payload["sub"]))
    except (ValueError, TypeError) as e:
        raise SocketAuthError("Subject del token inválido.") from e

    factory = get_session_factory()
    with factory() as db:
        user = db.get(User, uid)
        if user is None or not user.is_active:
            raise SocketAuthError("Usuario no encontrado o inactivo.")
        db.expunge(user)
        return user
