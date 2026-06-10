"""Utilidades HTTP para registrar rate limits y propagar 429."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.services.rate_limit_audit import record_rate_limit_event

if TYPE_CHECKING:
    pass


def record_http_rate_limit_if_429(
    exc: BaseException,
    db: Session,
    *,
    settings: Settings,
    user_id: uuid.UUID | None,
    ip_address: str | None,
    endpoint: str,
    method: str,
) -> None:
    if not settings.rate_limit_audit_enabled:
        return
    if not isinstance(exc, HTTPException) or exc.status_code != 429:
        return
    detail = exc.detail if isinstance(exc.detail, dict) else {}
    reason = str(detail.get("message", "RATE_LIMITED"))
    record_rate_limit_event(
        db,
        user_id=user_id,
        ip_address=ip_address,
        endpoint=endpoint,
        method=method,
        reason=reason,
    )
