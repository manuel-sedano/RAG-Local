"""Dependencias FastAPI (DB, usuario actual, roles, acceso a KB)."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Generator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.knowledge_base import KnowledgeBase, KbMembership
from app.models.user import User
from app.services.jwt_tokens import decode_access_token

security = HTTPBearer(auto_error=False)

_ROLE_ORDER = {"viewer": 1, "editor": 2, "owner": 3}


def get_db(request: Request) -> Generator[Session, None, None]:
    factory = request.app.state.db_session_factory
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_redis(request: Request):
    return getattr(request.app.state, "redis_client", None)


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_TOKEN_INVALID",
                "message": "Falta el encabezado Authorization Bearer.",
                "details": {},
            },
        )
    payload = decode_access_token(creds.credentials, settings)
    try:
        uid = uuid.UUID(str(payload["sub"]))
    except (ValueError, TypeError) as e:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_TOKEN_INVALID",
                "message": "Token de acceso inválido.",
                "details": {},
            },
        ) from e
    user = db.get(User, uid)
    if user is None or not user.is_active:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_TOKEN_INVALID",
                "message": "Usuario no encontrado o inactivo.",
                "details": {},
            },
        )
    return user


def require_app_roles(*roles: str) -> Callable[..., User]:
    allowed = set(roles)

    def _dep(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "AUTH_FORBIDDEN",
                    "message": "No tienes permisos para esta operación.",
                    "details": {"required_roles": list(roles)},
                },
            )
        return user

    return _dep


def _assert_kb_access(db: Session, user: User, kb_id: uuid.UUID, *, min_role: str) -> None:
    if min_role not in _ROLE_ORDER:
        msg = f"Rol mínimo de KB desconocido: {min_role}"
        raise ValueError(msg)
    need = _ROLE_ORDER[min_role]

    if user.role == "admin":
        kb = db.get(KnowledgeBase, kb_id)
        if kb is None or kb.deleted_at is not None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "KB_NOT_FOUND",
                    "message": "La base de conocimiento no existe.",
                    "details": {},
                },
            )
        return

    kb = db.get(KnowledgeBase, kb_id)
    if kb is None or kb.deleted_at is not None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={
                "code": "KB_NOT_FOUND",
                "message": "La base de conocimiento no existe.",
                "details": {},
            },
        )

    if kb.owner_user_id == user.id:
        if _ROLE_ORDER["owner"] < need:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "AUTH_FORBIDDEN",
                    "message": "Permisos insuficientes en esta base de conocimiento.",
                    "details": {"kb_id": str(kb_id)},
                },
            )
        return

    q = select(KbMembership).where(
        KbMembership.kb_id == kb_id,
        KbMembership.user_id == user.id,
    )
    m = db.execute(q).scalar_one_or_none()
    if m is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "code": "AUTH_FORBIDDEN",
                "message": "No tienes acceso a esta base de conocimiento.",
                "details": {"kb_id": str(kb_id)},
            },
        )
    if _ROLE_ORDER.get(m.role, 0) < need:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "code": "AUTH_FORBIDDEN",
                "message": "Permisos insuficientes en esta base de conocimiento.",
                "details": {"kb_id": str(kb_id)},
            },
        )


def require_kb_access(min_role: str = "viewer") -> Callable[..., uuid.UUID]:
    """Valida acceso a la KB del path `kb_id`; devuelve el mismo `kb_id`."""

    def _dep(
        kb_id: uuid.UUID,
        user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)],
    ) -> uuid.UUID:
        _assert_kb_access(db, user, kb_id, min_role=min_role)
        return kb_id

    return _dep


def ensure_kb_access(
    kb_id: uuid.UUID,
    user: User,
    db: Session,
    *,
    min_role: str = "viewer",
) -> None:
    """Uso en servicios cuando no conviene `Depends`."""
    _assert_kb_access(db, user, kb_id, min_role=min_role)
