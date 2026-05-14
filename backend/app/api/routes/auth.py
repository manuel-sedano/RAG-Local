"""Endpoints de autenticación (login, refresh, logout)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_redis
from app.core.config import Settings, get_settings
from app.models.user import User
from app.services.auth_audit import log_security_event
from app.services.auth_service import (
    authenticate_user,
    issue_tokens_for_user,
    logout_user,
    normalize_email,
    rotate_refresh_token,
    user_to_public,
)
from app.services.login_rate_limit import (
    check_login_rate_limits,
    check_refresh_rate_limit,
    check_user_lockout,
    clear_password_fail_counters,
    record_failed_password_attempt,
)

router = APIRouter(prefix="/auth", tags=["auth"])
strict_bearer = HTTPBearer()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10)


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LogoutRequest(BaseModel):
    refresh_token: str | None = None
    all_devices: bool = False


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


@router.post("/login", response_model=LoginResponse)
def post_login(
    request: Request,
    body: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    redis_client = get_redis(request)
    ip = _client_ip(request) or "unknown"
    email_n = normalize_email(str(body.email))
    check_login_rate_limits(redis_client, settings=settings, ip=ip, email_normalized=email_n)

    user = db.execute(select(User).where(User.email == email_n)).scalar_one_or_none()
    if user is not None:
        check_user_lockout(redis_client, settings=settings, user_id=str(user.id))

    auth_user = authenticate_user(db, email=email_n, password=body.password, settings=settings)
    if auth_user is None:
        if user is not None:
            record_failed_password_attempt(
                redis_client,
                settings=settings,
                user_id=str(user.id),
            )
            log_security_event(
                db,
                kind="LOGIN_FAILED",
                user_id=user.id,
                ip_address=ip,
                details={"reason": "invalid_password"},
            )
        else:
            log_security_event(
                db,
                kind="LOGIN_FAILED",
                user_id=None,
                ip_address=ip,
                details={"reason": "unknown_email"},
            )
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_INVALID_CREDENTIALS",
                "message": "Credenciales inválidas.",
                "details": {},
            },
        )

    if not auth_user.is_active:
        log_security_event(
            db,
            kind="LOGIN_FAILED",
            user_id=auth_user.id,
            ip_address=ip,
            details={"reason": "inactive"},
        )
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_INVALID_CREDENTIALS",
                "message": "Credenciales inválidas.",
                "details": {},
            },
        )

    clear_password_fail_counters(redis_client, user_id=str(auth_user.id))
    ua = request.headers.get("user-agent")
    access, refresh = issue_tokens_for_user(
        db,
        settings=settings,
        user=auth_user,
        ip_address=ip,
        user_agent=ua,
    )
    log_security_event(
        db,
        kind="LOGIN_SUCCESS",
        user_id=auth_user.id,
        ip_address=ip,
        details={},
    )
    return LoginResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expires_seconds,
        user=user_to_public(auth_user),
    )


@router.post("/refresh", response_model=RefreshResponse)
def post_refresh(
    request: Request,
    body: RefreshRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RefreshResponse:
    redis_client = get_redis(request)
    ip = _client_ip(request) or "unknown"
    check_refresh_rate_limit(redis_client, settings=settings, ip=ip)
    ua = request.headers.get("user-agent")
    access, refresh = rotate_refresh_token(
        db,
        settings=settings,
        raw_refresh=body.refresh_token.strip(),
        ip_address=ip,
        user_agent=ua,
    )
    return RefreshResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expires_seconds,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def post_logout(
    request: Request,
    body: LogoutRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    creds: Annotated[HTTPAuthorizationCredentials, Depends(strict_bearer)],
) -> None:
    ip = _client_ip(request) or "unknown"
    raw = body.refresh_token.strip() if body.refresh_token else None
    logout_user(
        db,
        settings=settings,
        access_token=creds.credentials,
        raw_refresh=raw,
        all_devices=body.all_devices,
        ip_address=ip,
    )
