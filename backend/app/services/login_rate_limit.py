"""Endpoints de autenticación (login, refresh, logout)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_redis, get_settings
from app.core.config import Settings
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
                details={"reason": "unknown_email", "email": email_n},
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
    # Rate limit refresh por IP (reutiliza contadores de login por simplicidad)
    check_login_rate_limits(
        redis_client,
        settings=settings,
        ip=ip,
        email_normalized=f"refresh:{ip}",
    )
    ua = request.headers.get("user-agent")
    access, refresh = rotate_refresh_token(
        db,
        settings=settings,
        raw_refresh=body.refresh_token.strip(),
        ip_address=ip,
        user_agent=ua,
    )
    log_security_event(
        db,
        kind="TOKEN_REFRESH",
        user_id=None,
        ip_address=ip,
        details={},
    )
    # user_id en TOKEN_REFRESH: inferir desde token si hace falta; dejamos null por simplicidad
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
    logout_user(
        db,
        settings=settings,
        access_token=creds.credentials,
        raw_refresh=body.refresh_token.strip() if body.refresh_token else None,
        all_devices=body.all_devices,
        ip_address=ip,
    )
    log_security_event(
        db,
        kind="LOGOUT",
        user_id=None,
        ip_address=ip,
        details={"note": "duplicate_audit_if_service_logged"},
    )
```

Wait - logout_user already logs LOGOUT in auth_service. I'm double-logging in route - remove the extra log_security_event from route for logout.

Also TOKEN_REFRESH - should log with user id from the rotated token's user. I can decode new access... or get from old row before rotate returns - simplest: in rotate_refresh_token return user id or log inside rotate. I'll move TOKEN_REFRESH log into rotate_refresh_token after we have user.

And fix refresh rate limit - using email_normalized=f"refresh:{ip}" pollutes - better skip email bucket for refresh or use dedicated keys. Simpler: only check IP for refresh with a separate function or pass a flag.

I'll add `check_refresh_rate_limit` that only increments IP key or use same IP limit with separate key prefix `auth:rl:refresh:ip:`.

Quick fix in login_rate_limit.py:
```python
def check_refresh_rate_limit(redis_client, settings, ip: str):
    bucket = _minute_bucket()
    key = f"auth:rl:refresh:ip:{ip}:{bucket}"
    ...
    same limits as IP for login
```

Or simpler: remove rate limit from refresh endpoint for now (token is secret) - only brute force if refresh leaks. I'll use lighter limit - just IP incr with same max as login.

Actually I'll add `check_simple_ip_limit` in login_rate_limit.py for refresh.

For TOKEN_REFRESH audit with user_id: update rotate_refresh_token to accept db and log, or return user id.

I'll add log in rotate_refresh_token at end:
```python
log_security_event(db, kind="TOKEN_REFRESH", user_id=user.id, ...)
```

Remove from route.

**logout route** - remove duplicate audit - auth_service.logout_user already logs. Good.

**LOGIN_FAILED unknown_email** - logging email in details might be privacy concern - use hash or omit. I'll use details={"reason": "unknown_email"} only.

**get_settings in deps** - I used `from app.api.deps import get_db, get_redis, get_settings` but get_settings is in app.core.config - fix import in auth.py to `from app.core.config import get_settings`

**post_refresh TOKEN_REFRESH** - add logging inside rotate_refresh_token

Let me update auth_service rotate to log TOKEN_REFRESH with user.id

And fix auth routes imports and remove refresh email hack - add check_refresh_ip_rate in login_rate_limit

Also **logout_user** already calls log_security_event for LOGOUT - route should not duplicate. I removed duplicate from route in my mind - the draft had duplicate - fix.

**logout route** - remove the erroneous log at end of post_logout.

**rotate_refresh_token** - add:
```python
from app.services.auth_audit import log_security_event
...
log_security_event(db, kind="TOKEN_REFRESH", user_id=user.id, ip_address=ip_address, details={})
```

**refresh rate limit** - add function only IP based with key auth:rl:refresh:ip

Let me add `check_refresh_rate_limit` to login_rate_limit.py

Also fix auth.py import get_settings from core.config

Fix post_refresh to use check_refresh_rate_limit

Remove unused Header import if any

**Security**: LOGIN_FAILED with unknown_email - don't store raw email in DB for GDPR - I'll use reason only.

Implement fixes.

Corrigiendo imports en `auth.py`, añadiendo límite de refresh por IP, registrando `TOKEN_REFRESH` en el servicio y eliminando la auditoría duplicada en logout.


StrReplace