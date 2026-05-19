"""Chats por KB: sesiones e historial de mensajes."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_kb_access
from app.models.chat import Chat, ChatMessage
from app.models.user import User
from app.services.chat_paths import build_file_path, build_viewer_path
from app.services.chat_service import (
    create_chat,
    get_chat_for_kb,
    list_chats_for_kb,
    list_messages_for_chat,
)

router = APIRouter(prefix="/kbs/{kb_id}/chats", tags=["chats"])


def _iso_z(dt: Any) -> str:
    return dt.isoformat().replace("+00:00", "Z")


class ChatCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=2048)

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None


class ChatCreateResponse(BaseModel):
    chat_id: uuid.UUID
    title: str | None
    created_at: str


class ChatListItem(BaseModel):
    chat_id: uuid.UUID
    title: str | None
    created_at: str
    updated_at: str


class ChatListResponse(BaseModel):
    items: list[ChatListItem]


class ChatDetailResponse(BaseModel):
    chat_id: uuid.UUID
    kb_id: uuid.UUID
    title: str | None
    created_by_user_id: uuid.UUID
    created_at: str
    updated_at: str


class CitationResponse(BaseModel):
    document_id: uuid.UUID
    chunk_id: uuid.UUID
    filename_original: str
    mime_type: str
    page_start: int | None
    page_end: int | None
    score: float
    viewer_path: str
    file_path: str


class MessageItemResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: str
    citations: list[CitationResponse] | None = None


class MessageListResponse(BaseModel):
    items: list[MessageItemResponse]


def _chat_not_found() -> HTTPException:
    return HTTPException(
        status.HTTP_404_NOT_FOUND,
        detail={
            "code": "CHAT_NOT_FOUND",
            "message": "El chat no existe en esta base de conocimiento.",
            "details": {},
        },
    )


def _chat_to_list_item(chat: Chat) -> ChatListItem:
    return ChatListItem(
        chat_id=chat.id,
        title=chat.title,
        created_at=_iso_z(chat.created_at),
        updated_at=_iso_z(chat.updated_at),
    )


def _chat_to_detail(chat: Chat) -> ChatDetailResponse:
    return ChatDetailResponse(
        chat_id=chat.id,
        kb_id=chat.kb_id,
        title=chat.title,
        created_by_user_id=chat.created_by_user_id,
        created_at=_iso_z(chat.created_at),
        updated_at=_iso_z(chat.updated_at),
    )


def _citation_to_response(kb_id: uuid.UUID, citation: Any) -> CitationResponse:
    doc = citation.document
    return CitationResponse(
        document_id=citation.document_id,
        chunk_id=citation.chunk_id,
        filename_original=doc.filename_original,
        mime_type=doc.mime_type,
        page_start=citation.page_start,
        page_end=citation.page_end,
        score=citation.score,
        viewer_path=build_viewer_path(kb_id, citation.document_id, page_start=citation.page_start),
        file_path=build_file_path(kb_id, citation.document_id),
    )


def _message_to_item(kb_id: uuid.UUID, msg: ChatMessage) -> MessageItemResponse:
    citations: list[CitationResponse] | None = None
    if msg.role == "assistant" and msg.citations:
        citations = [_citation_to_response(kb_id, c) for c in msg.citations]
    return MessageItemResponse(
        id=msg.id,
        role=msg.role,
        content=msg.content,
        created_at=_iso_z(msg.created_at),
        citations=citations,
    )


@router.post("", response_model=ChatCreateResponse, status_code=status.HTTP_201_CREATED)
def post_chat(
    kb_id: Annotated[uuid.UUID, Depends(require_kb_access("viewer"))],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    body: ChatCreateRequest,
) -> ChatCreateResponse:
    chat = create_chat(db, kb_id=kb_id, user=user, title=body.title)
    return ChatCreateResponse(
        chat_id=chat.id,
        title=chat.title,
        created_at=_iso_z(chat.created_at),
    )


@router.get("", response_model=ChatListResponse)
def get_chats(
    kb_id: Annotated[uuid.UUID, Depends(require_kb_access("viewer"))],
    db: Annotated[Session, Depends(get_db)],
) -> ChatListResponse:
    rows = list_chats_for_kb(db, kb_id)
    return ChatListResponse(items=[_chat_to_list_item(c) for c in rows])


@router.get("/{chat_id}", response_model=ChatDetailResponse)
def get_chat(
    kb_id: Annotated[uuid.UUID, Depends(require_kb_access("viewer"))],
    chat_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> ChatDetailResponse:
    chat = get_chat_for_kb(db, kb_id=kb_id, chat_id=chat_id)
    if chat is None:
        raise _chat_not_found()
    return _chat_to_detail(chat)


@router.get("/{chat_id}/messages", response_model=MessageListResponse)
def get_chat_messages(
    kb_id: Annotated[uuid.UUID, Depends(require_kb_access("viewer"))],
    chat_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> MessageListResponse:
    chat = get_chat_for_kb(db, kb_id=kb_id, chat_id=chat_id)
    if chat is None:
        raise _chat_not_found()
    messages = list_messages_for_chat(db, chat_id)
    return MessageListResponse(items=[_message_to_item(kb_id, m) for m in messages])
