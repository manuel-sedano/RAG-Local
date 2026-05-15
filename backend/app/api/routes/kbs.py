"""CRUD de bases de conocimiento (`/api/kbs`)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_kb_access
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User
from app.services.kb_service import (
    create_knowledge_base,
    list_knowledge_bases_for_user,
    soft_delete_knowledge_base,
    update_knowledge_base,
)

router = APIRouter(prefix="/kbs", tags=["knowledge-bases"])


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


class KbListItem(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: str
    updated_at: str


class KbListResponse(BaseModel):
    items: list[KbListItem]


class KbCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=2048)
    description: str | None = Field(default=None, max_length=32_768)

    @field_validator("name")
    @classmethod
    def strip_name_create(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("El nombre no puede quedar vacío.")
        return s

    @field_validator("description")
    @classmethod
    def strip_desc_create(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None


class KbCreateResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None


class KbPatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=2048)
    description: str | None = Field(default=None, max_length=32_768)

    @field_validator("name")
    @classmethod
    def strip_name_patch(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.strip()

    @field_validator("description")
    @classmethod
    def strip_desc_patch(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        return s or None


def _kb_to_list_item(kb: KnowledgeBase) -> KbListItem:
    return KbListItem(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        created_at=kb.created_at.isoformat().replace("+00:00", "Z"),
        updated_at=kb.updated_at.isoformat().replace("+00:00", "Z"),
    )


@router.get("", response_model=KbListResponse)
def get_kbs(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> KbListResponse:
    rows = list_knowledge_bases_for_user(db, user)
    return KbListResponse(items=[_kb_to_list_item(kb) for kb in rows])


@router.post("", response_model=KbCreateResponse, status_code=status.HTTP_201_CREATED)
def post_kb(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    body: KbCreateRequest,
) -> KbCreateResponse:
    kb = create_knowledge_base(
        db,
        user,
        name=body.name,
        description=body.description,
        ip_address=_client_ip(request),
    )
    return KbCreateResponse(id=kb.id, name=kb.name, description=kb.description)


@router.get("/{kb_id}", response_model=KbListItem)
def get_kb(
    kb_id: Annotated[uuid.UUID, Depends(require_kb_access("viewer"))],
    db: Annotated[Session, Depends(get_db)],
) -> KbListItem:
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
    return _kb_to_list_item(kb)


@router.patch("/{kb_id}", response_model=KbListItem)
def patch_kb(
    request: Request,
    kb_id: Annotated[uuid.UUID, Depends(require_kb_access("editor"))],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    body: KbPatchRequest,
) -> KbListItem:
    fields = body.model_fields_set
    if not fields:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Debes enviar al menos un campo para actualizar.",
                "details": {},
            },
        )
    if "name" in fields and body.name is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "El nombre no puede quedar vacío.",
                "details": {},
            },
        )

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

    name_val = body.name if "name" in fields else None
    unset_description = "description" in fields and body.description is None
    desc_val = (
        body.description if "description" in fields and body.description is not None else None
    )

    update_knowledge_base(
        db,
        kb,
        user,
        name=name_val if "name" in fields else None,
        description=desc_val,
        unset_description=unset_description,
        ip_address=_client_ip(request),
    )
    db.refresh(kb)
    return _kb_to_list_item(kb)


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kb(
    request: Request,
    kb_id: Annotated[uuid.UUID, Depends(require_kb_access("owner"))],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
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
    soft_delete_knowledge_base(db, kb, user, ip_address=_client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
