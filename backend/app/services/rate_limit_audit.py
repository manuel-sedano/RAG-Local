"""Persistencia de eventos de rate limit en `rate_limit_events`."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models.audit import RateLimitEvent

if TYPE_CHECKING:
    pass


def record_rate_limit_event(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    ip_address: str | None,
    endpoint: str,
    method: str,
    reason: str,
) -> None:
    """Registra un evento de rate limit (best-effort; no debe romper la respuesta 429)."""
    row = RateLimitEvent(
        user_id=user_id,
        ip_address=ip_address,
        endpoint=endpoint,
        method=method,
        reason=reason,
    )
    db.add(row)
