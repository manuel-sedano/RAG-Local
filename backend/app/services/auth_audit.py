"""Auditoría de eventos de autenticación (`security_events`)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import SecurityEvent


def log_security_event(
    db: Session,
    *,
    kind: str,
    user_id: uuid.UUID | None,
    ip_address: str | None,
    details: dict[str, Any],
) -> None:
    row = SecurityEvent(
        user_id=user_id,
        ip_address=ip_address,
        kind=kind,
        details=details,
    )
    db.add(row)
