"""Operaciones de negocio para bases de conocimiento (listado, CRUD, soft delete)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.knowledge_base import KbMembership, KnowledgeBase
from app.models.user import User
from app.services.auth_audit import log_security_event


def list_knowledge_bases_for_user(db: Session, user: User) -> list[KnowledgeBase]:
    """KB no eliminadas: propias, con membresía, o todas si el usuario es admin."""
    q = select(KnowledgeBase).where(KnowledgeBase.deleted_at.is_(None))
    if user.role != "admin":
        member_kb_ids = select(KbMembership.kb_id).where(KbMembership.user_id == user.id)
        q = q.where(
            or_(
                KnowledgeBase.owner_user_id == user.id,
                KnowledgeBase.id.in_(member_kb_ids),
            )
        )
    q = q.order_by(KnowledgeBase.updated_at.desc())
    return list(db.execute(q).scalars().all())


def create_knowledge_base(
    db: Session,
    user: User,
    *,
    name: str,
    description: str | None,
    ip_address: str | None,
) -> KnowledgeBase:
    kb = KnowledgeBase(
        name=name.strip(),
        description=(description.strip() if description else None) or None,
        owner_user_id=user.id,
    )
    db.add(kb)
    db.flush()
    log_security_event(
        db,
        kind="KB_CREATED",
        user_id=user.id,
        ip_address=ip_address,
        details={"kb_id": str(kb.id), "name": kb.name},
    )
    return kb


def update_knowledge_base(
    db: Session,
    kb: KnowledgeBase,
    user: User,
    *,
    name: str | None,
    description: str | None,
    unset_description: bool,
    ip_address: str | None,
) -> KnowledgeBase:
    details: dict[str, Any] = {"kb_id": str(kb.id)}
    if name is not None:
        kb.name = name.strip()
        details["name"] = kb.name
    if unset_description:
        kb.description = None
        details["description"] = None
    elif description is not None:
        kb.description = description.strip() or None
        details["description"] = kb.description
    db.flush()
    log_security_event(
        db,
        kind="KB_UPDATED",
        user_id=user.id,
        ip_address=ip_address,
        details=details,
    )
    return kb


def soft_delete_knowledge_base(
    db: Session,
    kb: KnowledgeBase,
    user: User,
    *,
    ip_address: str | None,
) -> None:
    kb.deleted_at = datetime.now(UTC)
    db.flush()
    log_security_event(
        db,
        kind="KB_DELETED",
        user_id=user.id,
        ip_address=ip_address,
        details={"kb_id": str(kb.id), "name": kb.name},
    )
