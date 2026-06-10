"""Chats por KB: sesiones e historial de mensajes."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_kb_access
from app.core.config import Settings, get_settings
from app.models.chat import Chat, ChatMessage, MessageCitation
from app.models.user import User
from app.services.chat import RagRequestConfig, generate_chat_reply
from app.services.chat.prompt_guards import assess_user_query, build_safety_flags
from app.services.chat.streaming import schedule_chat_stream_task
from app.services.chat_paths import build_file_path, build_viewer_path
from app.services.chat_service import (
    create_chat,
    get_chat_for_kb,
    list_chats_for_kb,
    list_messages_for_chat,
    touch_chat_updated_at,
)
from app.services.retrieval import SearchFilters

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


class SafetyFlagsResponse(BaseModel):
    user_query_blocked: bool | None = None
    ignored_chunks: int | None = None
    user_notice: str | None = None
    reasons: list[str] | None = None


class MessageItemResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: str
    citations: list[CitationResponse] | None = None
    safety_flags: SafetyFlagsResponse | None = None


class MessageListResponse(BaseModel):
    items: list[MessageItemResponse]


class RagConfigBody(BaseModel):
    top_k: int | None = Field(default=None, ge=1, le=50)
    rerank_top_k: int | None = Field(default=None, ge=1, le=50)
    hybrid: bool | None = None
    filters: dict[str, Any] | None = None


class PostMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=32_768)
    stream: bool = False
    rag: RagConfigBody | None = None

    @field_validator("content")
    @classmethod
    def strip_content(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("El mensaje no puede quedar vacío.")
        return s


class MessageUsageResponse(BaseModel):
    prompt_tokens: int
    completion_tokens: int


class PostMessageResponse(BaseModel):
    message_id: uuid.UUID
    role: str
    content: str
    citations: list[CitationResponse]
    usage: MessageUsageResponse | None = None
    safety_flags: SafetyFlagsResponse | None = None


class PostMessageStreamResponse(BaseModel):
    message_id: uuid.UUID
    status: str
    socket: dict[str, str]


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


def _rag_config_from_body(body: RagConfigBody | None) -> RagRequestConfig | None:
    if body is None:
        return None
    filters = None
    if body.filters:
        tags = body.filters.get("tags") or []
        mime_types = body.filters.get("mime_types") or body.filters.get("mime_type")
        if isinstance(mime_types, str):
            mime_types = [mime_types]
        filters = SearchFilters(
            tags=list(tags) if tags else [],
            mime_types=list(mime_types) if mime_types else [],
            source=body.filters.get("source"),
        )
    return RagRequestConfig(
        top_k=body.top_k,
        rerank_top_k=body.rerank_top_k,
        hybrid=body.hybrid,
        filters=filters,
    )


def _citations_for_message(
    kb_id: uuid.UUID,
    citations: list[MessageCitation],
) -> list[CitationResponse]:
    return [_citation_to_response(kb_id, c) for c in citations]


def _safety_flags_to_response(flags: dict | None) -> SafetyFlagsResponse | None:
    if not flags:
        return None
    reasons = flags.get("reasons")
    if isinstance(reasons, list):
        reason_list = [str(r) for r in reasons]
    else:
        reason_list = None
    return SafetyFlagsResponse(
        user_query_blocked=flags.get("user_query_blocked"),
        ignored_chunks=flags.get("ignored_chunks"),
        user_notice=flags.get("user_notice"),
        reasons=reason_list,
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
        safety_flags=_safety_flags_to_response(msg.safety_flags),
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


@router.post(
    "/{chat_id}/messages",
    responses={
        200: {"model": PostMessageResponse},
        202: {"model": PostMessageStreamResponse},
    },
)
async def post_chat_message(
    request: Request,
    kb_id: Annotated[uuid.UUID, Depends(require_kb_access("viewer"))],
    chat_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    body: PostMessageRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PostMessageResponse:
    _ = user
    chat = get_chat_for_kb(db, kb_id=kb_id, chat_id=chat_id)
    if chat is None:
        raise _chat_not_found()

    if body.stream:
        user_guard = assess_user_query(body.content, settings)
        if user_guard.blocked:
            user_msg = ChatMessage(chat_id=chat.id, role="user", content=body.content)
            db.add(user_msg)
            db.flush()
            refusal = user_guard.refusal_message or (
                "No puedo ayudar con esa solicitud por políticas de seguridad."
            )
            flags = build_safety_flags(user_guard=user_guard)
            assistant_msg = ChatMessage(
                chat_id=chat.id,
                role="assistant",
                content=refusal,
                model=settings.llm_model,
                safety_flags=flags,
            )
            db.add(assistant_msg)
            db.flush()
            touch_chat_updated_at(db, chat)
            db.commit()
            return PostMessageResponse(
                message_id=assistant_msg.id,
                role="assistant",
                content=refusal,
                citations=[],
                usage=MessageUsageResponse(
                    prompt_tokens=0,
                    completion_tokens=max(1, len(refusal) // 4),
                ),
                safety_flags=_safety_flags_to_response(flags),
            )

        user_msg = ChatMessage(chat_id=chat.id, role="user", content=body.content)
        db.add(user_msg)
        db.flush()
        assistant_msg = ChatMessage(
            chat_id=chat.id,
            role="assistant",
            content="",
            model=settings.llm_model,
        )
        db.add(assistant_msg)
        db.flush()
        touch_chat_updated_at(db, chat)
        db.commit()
        rag_cfg = _rag_config_from_body(body.rag)
        schedule_chat_stream_task(
            request.app,
            kb_id=kb_id,
            chat_id=chat_id,
            assistant_message_id=assistant_msg.id,
            user_content=body.content,
            rag=rag_cfg,
        )
        payload = PostMessageStreamResponse(
            message_id=assistant_msg.id,
            status="STREAMING",
            socket={
                "namespace": "/chat",
                "room": f"chat:{chat_id}",
            },
        )
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=payload.model_dump(mode="json"),
        )

    rag_cfg = _rag_config_from_body(body.rag)
    try:
        result = generate_chat_reply(
            db,
            settings,
            chat=chat,
            user_content=body.content,
            rag=rag_cfg,
        )
    except ValueError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "VALIDATION_ERROR",
                "message": str(e),
                "details": {},
            },
        ) from e

    usage_resp = None
    if result.usage:
        usage_resp = MessageUsageResponse(
            prompt_tokens=result.usage.get("prompt_tokens", 0),
            completion_tokens=result.usage.get("completion_tokens", 0),
        )

    return PostMessageResponse(
        message_id=result.assistant_message.id,
        role="assistant",
        content=result.assistant_message.content,
        citations=_citations_for_message(kb_id, result.citations),
        usage=usage_resp,
        safety_flags=_safety_flags_to_response(result.assistant_message.safety_flags),
    )
