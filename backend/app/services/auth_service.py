"""Lógica de login, refresh rotatorio y logout."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.user import RefreshToken, User
from app.services.auth_audit import log_security_event
from app.services.jwt_tokens import create_access_token, decode_access_token
from app.services.passwords import verify_password


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_opaque_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def authenticate_user(
    db: Session,
    *,
    email: str,
    password: str,
    settings: Settings,
) -> User | None:
    q = select(User).where(User.email == email)
    user = db.execute(q).scalar_one_or_none()
    if user is None:
        return None
    if not verify_password(password, user.password_hash, pepper=settings.password_pepper):
        return None
    return user


def issue_tokens_for_user(
    db: Session,
    *,
    settings: Settings,
    user: User,
    ip_address: str | None,
    user_agent: str | None,
) -> tuple[str, str]:
    """Crea fila `refresh_tokens` y devuelve `(access_jwt, refresh_opaco)`."""
    raw_refresh = new_opaque_refresh_token()
    th = hash_refresh_token(raw_refresh)
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=settings.jwt_refresh_token_expires_seconds)
    row = RefreshToken(
        user_id=user.id,
        token_hash=th,
        expires_at=expires_at,
        revoked_at=None,
        replaced_by_id=None,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(row)
    db.flush()
    access, _jti = create_access_token(
        settings=settings,
        user_id=user.id,
        email=user.email,
        role=user.role,
    )
    return access, raw_refresh


def rotate_refresh_token(
    db: Session,
    *,
    settings: Settings,
    raw_refresh: str,
    ip_address: str | None,
    user_agent: str | None,
) -> tuple[str, str]:
    """Invalida el refresh presentado y emite par nuevo."""
    th = hash_refresh_token(raw_refresh)
    q = select(RefreshToken).where(RefreshToken.token_hash == th)
    old = db.execute(q).scalar_one_or_none()
    if old is None or old.revoked_at is not None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_TOKEN_INVALID",
                "message": "Refresh token inválido o revocado.",
                "details": {},
            },
        )
    exp = old.expires_at
    exp = exp.replace(tzinfo=UTC) if exp.tzinfo is None else exp.astimezone(UTC)
    if exp < datetime.now(UTC):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_TOKEN_EXPIRED",
                "message": "Refresh token expirado.",
                "details": {},
            },
        )

    user = db.get(User, old.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_TOKEN_INVALID",
                "message": "Usuario no disponible.",
                "details": {},
            },
        )

    raw_new = new_opaque_refresh_token()
    th_new = hash_refresh_token(raw_new)
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=settings.jwt_refresh_token_expires_seconds)
    new_row = RefreshToken(
        user_id=user.id,
        token_hash=th_new,
        expires_at=expires_at,
        revoked_at=None,
        replaced_by_id=None,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(new_row)
    db.flush()
    old.revoked_at = now
    old.replaced_by_id = new_row.id

    access, _jti = create_access_token(
        settings=settings,
        user_id=user.id,
        email=user.email,
        role=user.role,
    )
    log_security_event(
        db,
        kind="TOKEN_REFRESH",
        user_id=user.id,
        ip_address=ip_address,
        details={},
    )
    return access, raw_new


def logout_user(
    db: Session,
    *,
    settings: Settings,
    access_token: str,
    raw_refresh: str | None,
    all_devices: bool,
    ip_address: str | None,
) -> None:
    payload = decode_access_token(access_token, settings)
    uid = uuid.UUID(str(payload["sub"]))
    user = db.get(User, uid)
    if user is None or not user.is_active:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_TOKEN_INVALID",
                "message": "Token de acceso inválido.",
                "details": {},
            },
        )

    now = datetime.now(UTC)
    if all_devices:
        q = select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        for row in db.execute(q).scalars():
            row.revoked_at = now
        log_security_event(
            db,
            kind="LOGOUT",
            user_id=user.id,
            ip_address=ip_address,
            details={"all_devices": True},
        )
        return

    if not raw_refresh:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Se requiere refresh_token salvo que all_devices sea true.",
                "details": {},
            },
        )

    th = hash_refresh_token(raw_refresh)
    q = select(RefreshToken).where(RefreshToken.token_hash == th)
    row = db.execute(q).scalar_one_or_none()
    if row is None or row.user_id != user.id:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_TOKEN_INVALID",
                "message": "Refresh token no coincide con la sesión.",
                "details": {},
            },
        )
    if row.revoked_at is None:
        row.revoked_at = now
    log_security_event(
        db,
        kind="LOGOUT",
        user_id=user.id,
        ip_address=ip_address,
        details={"all_devices": False},
    )


def user_to_public(user: User) -> dict[str, Any]:
    return {"id": str(user.id), "email": user.email, "role": user.role}
