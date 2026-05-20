"""Operaciones de negocio para chats y mensajes (CRUD por KB)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.chat import Chat, ChatMessage, MessageCitation
from app.models.user import User


def create_chat(
    db: Session,
    *,
    kb_id: uuid.UUID,
    user: User,
    title: str | None,
) -> Chat:
    chat = Chat(
        kb_id=kb_id,
        created_by_user_id=user.id,
        title=(title.strip() if title else None) or None,
    )
    db.add(chat)
    db.flush()
    return chat


def list_chats_for_kb(db: Session, kb_id: uuid.UUID) -> list[Chat]:
    q = (
        select(Chat)
        .where(Chat.kb_id == kb_id, Chat.deleted_at.is_(None))
        .order_by(Chat.updated_at.desc())
    )
    return list(db.execute(q).scalars().all())


def get_chat_for_kb(
    db: Session,
    *,
    kb_id: uuid.UUID,
    chat_id: uuid.UUID,
) -> Chat | None:
    chat = db.get(Chat, chat_id)
    if chat is None or chat.deleted_at is not None or chat.kb_id != kb_id:
        return None
    return chat


def list_messages_for_chat(db: Session, chat_id: uuid.UUID) -> list[ChatMessage]:
    q = (
        select(ChatMessage)
        .where(ChatMessage.chat_id == chat_id)
        .options(
            selectinload(ChatMessage.citations).selectinload(MessageCitation.document),
            selectinload(ChatMessage.citations).selectinload(MessageCitation.chunk),
        )
        .order_by(ChatMessage.created_at.asc())
    )
    return list(db.execute(q).scalars().all())


def touch_chat_updated_at(db: Session, chat: Chat) -> None:
    chat.updated_at = datetime.now(UTC)
    db.flush()
