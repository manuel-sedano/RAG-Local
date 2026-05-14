"""JWT de acceso (HS256) con `jti`."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import HTTPException, status

from app.core.config import Settings


def create_access_token(
    *,
    settings: Settings,
    user_id: uuid.UUID,
    email: str,
    role: str,
) -> tuple[str, str]:
    """Devuelve `(token, jti)`."""
    jti = str(uuid.uuid4())
    now = datetime.now(UTC)
    exp = now + timedelta(seconds=settings.jwt_access_token_expires_seconds)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "type": "access",
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_alg,
    )
    if isinstance(token, bytes):
        token = token.decode("ascii")
    return token, jti


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_alg],
            options={"require": ["exp", "iat", "sub", "jti"]},
        )
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_TOKEN_EXPIRED",
                "message": "El token de acceso ha expirado.",
                "details": {},
            },
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_TOKEN_INVALID",
                "message": "Token de acceso inválido.",
                "details": {},
            },
        ) from e
