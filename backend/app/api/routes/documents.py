"""Documentos por KB: upload, listado, descarga, reindex y borrado lógico."""

from __future__ import annotations

import uuid
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_kb_access
from app.core.config import Settings, get_settings
from app.models.user import User
from app.services.document_service import (
    absolute_storage_path,
    ascii_fallback_filename,
    create_document_after_upload,
    disposition_from_query,
    find_duplicate_sha256,
    get_document_for_kb,
    list_documents,
    parse_tags_field,
    safe_filename_original,
    save_upload_stream,
    soft_delete_document,
    status_payload,
)
from app.tasks.ingest import ingest_document

router = APIRouter(prefix="/kbs/{kb_id}/documents", tags=["documents"])


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    status: str
    ingestion_job_id: str


class DocumentReindexResponse(BaseModel):
    document_id: uuid.UUID
    status: str
    ingestion_job_id: str


class DocumentListItem(BaseModel):
    id: uuid.UUID
    kb_id: uuid.UUID
    filename_original: str
    mime_type: str
    size_bytes: int
    status: str
    page_count: int | None
    chunk_count: int | None
    created_at: str


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    next_cursor: str | None = None


class DocumentDetailResponse(BaseModel):
    id: uuid.UUID
    kb_id: uuid.UUID
    filename_original: str
    mime_type: str
    size_bytes: int
    status: str
    page_count: int | None
    chunk_count: int | None
    language: str | None
    source: str | None
    tags: list[Any] | dict[str, Any] | None
    created_at: str
    updated_at: str


def _iso_z(dt: Any) -> str:
    return dt.isoformat().replace("+00:00", "Z")


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    request: Request,
    kb_id: Annotated[uuid.UUID, Depends(require_kb_access("editor"))],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File(...)],
    tags: Annotated[str | None, Form()] = None,
    source: Annotated[str | None, Form()] = None,
    language: Annotated[str | None, Form()] = None,
) -> DocumentUploadResponse:
    declared = (file.content_type or "").split(";")[0].strip().lower()
    if not declared:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "code": "UPLOAD_INVALID_TYPE",
                "message": "Falta Content-Type en el archivo.",
                "details": {},
            },
        )

    canonical = next(
        (m for m in settings.allowed_mime_type_list if m.lower() == declared),
        None,
    )
    if canonical is None:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "code": "UPLOAD_INVALID_TYPE",
                "message": "Tipo de archivo no permitido.",
                "details": {"mime_type": declared},
            },
        )

    try:
        tags_parsed = parse_tags_field(tags)
    except ValueError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": str(e),
                "details": {},
            },
        ) from e

    src = source.strip()[:8192] if source and source.strip() else None
    lang = language.strip()[:16] if language and language.strip() else None
    max_bytes = settings.max_upload_mb * 1024 * 1024
    fname = safe_filename_original(file.filename)

    try:
        _abs_path, rel_path, size_b, sha256 = await save_upload_stream(
            settings=settings,
            kb_id=kb_id,
            declared_mime=canonical,
            file_obj=file,
            max_bytes=max_bytes,
        )
    except ValueError as e:
        code = str(e)
        if code == "UPLOAD_TOO_LARGE":
            raise HTTPException(
                status.HTTP_413_CONTENT_TOO_LARGE,
                detail={
                    "code": "UPLOAD_TOO_LARGE",
                    "message": f"El archivo supera el límite de {settings.max_upload_mb} MB.",
                    "details": {},
                },
            ) from e
        if code == "UPLOAD_INVALID_TYPE":
            raise HTTPException(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail={
                    "code": "UPLOAD_INVALID_TYPE",
                    "message": "El contenido no coincide con el tipo declarado.",
                    "details": {"mime_type": canonical},
                },
            ) from e
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"code": "UPLOAD_ERROR", "message": str(e), "details": {}},
        ) from e

    if find_duplicate_sha256(db, kb_id=kb_id, sha256=sha256):
        abs_dup = absolute_storage_path(settings, rel_path)
        abs_dup.unlink(missing_ok=True)
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "code": "DUPLICATE_DOCUMENT",
                "message": "Ya existe un documento activo con el mismo contenido en esta KB.",
                "details": {"sha256": sha256},
            },
        )

    try:
        doc = create_document_after_upload(
            db,
            settings,
            kb_id=kb_id,
            user=user,
            filename_original=fname,
            storage_rel_path=rel_path,
            mime_type=canonical,
            size_bytes=size_b,
            sha256=sha256,
            tags=tags_parsed,
            source=src,
            language=lang,
            ip_address=_client_ip(request),
        )
    except ValueError as e:
        if str(e) == "DUPLICATE_DOCUMENT":
            absolute_storage_path(settings, rel_path).unlink(missing_ok=True)
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail={
                    "code": "DUPLICATE_DOCUMENT",
                    "message": "Ya existe un documento activo con el mismo contenido en esta KB.",
                    "details": {},
                },
            ) from e
        absolute_storage_path(settings, rel_path).unlink(missing_ok=True)
        raise

    async_result = ingest_document.delay(str(doc.id))
    job_id = async_result.id if async_result else str(uuid.uuid4())

    return DocumentUploadResponse(
        document_id=doc.id,
        status=doc.status,
        ingestion_job_id=job_id,
    )


@router.get("", response_model=DocumentListResponse)
def get_documents(
    kb_id: Annotated[uuid.UUID, Depends(require_kb_access("viewer"))],
    db: Annotated[Session, Depends(get_db)],
    doc_status: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[uuid.UUID | None, Query()] = None,
) -> DocumentListResponse:
    allowed_status = {
        "UPLOADED",
        "PROCESSING",
        "READY",
        "FAILED",
        "QUARANTINED",
    }
    if doc_status and doc_status not in allowed_status:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Valor de status no válido.",
                "details": {},
            },
        )
    try:
        rows, next_c = list_documents(
            db, kb_id=kb_id, status=doc_status, limit=limit, cursor=cursor
        )
    except ValueError as e:
        if str(e) == "CURSOR_INVALID":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_CURSOR",
                    "message": "El cursor no es válido para esta KB.",
                    "details": {},
                },
            ) from e
        raise
    items = [
        DocumentListItem(
            id=r.id,
            kb_id=r.kb_id,
            filename_original=r.filename_original,
            mime_type=r.mime_type,
            size_bytes=int(r.size_bytes),
            status=r.status,
            page_count=r.page_count,
            chunk_count=r.chunk_count,
            created_at=_iso_z(r.created_at),
        )
        for r in rows
    ]
    return DocumentListResponse(items=items, next_cursor=str(next_c) if next_c else None)


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
def get_document(
    kb_id: Annotated[uuid.UUID, Depends(require_kb_access("viewer"))],
    doc_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> DocumentDetailResponse:
    doc = get_document_for_kb(db, kb_id=kb_id, doc_id=doc_id)
    if doc is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={
                "code": "DOCUMENT_NOT_FOUND",
                "message": "El documento no existe.",
                "details": {},
            },
        )
    return DocumentDetailResponse(
        id=doc.id,
        kb_id=doc.kb_id,
        filename_original=doc.filename_original,
        mime_type=doc.mime_type,
        size_bytes=int(doc.size_bytes),
        status=doc.status,
        page_count=doc.page_count,
        chunk_count=doc.chunk_count,
        language=doc.language,
        source=doc.source,
        tags=doc.tags,
        created_at=_iso_z(doc.created_at),
        updated_at=_iso_z(doc.updated_at),
    )


@router.get("/{doc_id}/status")
def get_document_status(
    kb_id: Annotated[uuid.UUID, Depends(require_kb_access("viewer"))],
    doc_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    doc = get_document_for_kb(db, kb_id=kb_id, doc_id=doc_id)
    if doc is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={
                "code": "DOCUMENT_NOT_FOUND",
                "message": "El documento no existe.",
                "details": {},
            },
        )
    return status_payload(doc)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    request: Request,
    kb_id: Annotated[uuid.UUID, Depends(require_kb_access("editor"))],
    doc_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    doc = get_document_for_kb(db, kb_id=kb_id, doc_id=doc_id)
    if doc is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={
                "code": "DOCUMENT_NOT_FOUND",
                "message": "El documento no existe.",
                "details": {},
            },
        )
    soft_delete_document(
        db,
        doc=doc,
        user=user,
        ip_address=_client_ip(request),
        settings=settings,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{doc_id}/file")
def download_document_file(
    kb_id: Annotated[uuid.UUID, Depends(require_kb_access("viewer"))],
    doc_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    disposition: Annotated[str | None, Query()] = None,
) -> FileResponse:
    doc = get_document_for_kb(db, kb_id=kb_id, doc_id=doc_id)
    if doc is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={
                "code": "DOCUMENT_NOT_FOUND",
                "message": "El documento no existe.",
                "details": {},
            },
        )
    if doc.status == "QUARANTINED":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "code": "DOCUMENT_QUARANTINED",
                "message": "El documento está en cuarentena y no puede servirse.",
                "details": {},
            },
        )
    path = absolute_storage_path(settings, doc.storage_path)
    if not path.is_file():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={
                "code": "DOCUMENT_FILE_MISSING",
                "message": "No se encontró el binario en almacenamiento.",
                "details": {},
            },
        )
    disp = disposition_from_query(disposition, doc.mime_type)
    fname = doc.filename_original
    ascii_name = ascii_fallback_filename(fname)
    utf8_q = quote(fname, safe="")
    cd = f"{disp}; filename=\"{ascii_name}\"; filename*=UTF-8''{utf8_q}"
    return FileResponse(
        path=str(path),
        media_type=doc.mime_type,
        headers={"Content-Disposition": cd},
    )


@router.post(
    "/{doc_id}/reindex",
    response_model=DocumentReindexResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Reintentar ingesta de un documento",
)
def reindex_document(
    kb_id: Annotated[uuid.UUID, Depends(require_kb_access("editor"))],
    doc_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> DocumentReindexResponse:
    """Encola una nueva corrida de ingesta (Celery) sin esperar al worker."""
    doc = get_document_for_kb(db, kb_id=kb_id, doc_id=doc_id)
    if doc is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={
                "code": "DOCUMENT_NOT_FOUND",
                "message": "El documento no existe.",
                "details": {},
            },
        )
    async_result = ingest_document.delay(str(doc.id))
    job_id = async_result.id if async_result else str(uuid.uuid4())
    return DocumentReindexResponse(
        document_id=doc.id,
        status=doc.status,
        ingestion_job_id=job_id,
    )
