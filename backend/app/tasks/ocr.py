"""Tareas Celery en cola `ocr` (OCR de documentos PDF)."""

from __future__ import annotations

import logging
import uuid

from celery import Task
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.session import get_engine
from app.models.document import Document
from app.services.document_service import absolute_storage_path, resolve_upload_root
from app.services.parsing.errors import ParserError, RecoverableParserError
from app.services.parsing.ocr import enrich_parsed_with_ocr
from app.services.parsing.orchestrator import parse_document_file
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_PDF = "application/pdf"


def _get_session_factory() -> sessionmaker[Session]:
    engine = get_engine()
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


@celery_app.task(bind=True, name="app.tasks.ocr.run_document_ocr")
def run_document_ocr(self: Task, document_id: str) -> dict[str, object]:
    """Ejecuta parse + OCR para un PDF (cola dedicada `ocr`).

    La ingesta principal llama a `enrich_parsed_with_ocr` inline; esta tarea
    permite reprocesar OCR o escalar workers `-Q ocr` por separado.
    """
    settings = get_settings()
    session_factory = _get_session_factory()
    session = session_factory()
    try:
        doc_uuid = uuid.UUID(document_id)
        document = session.get(Document, doc_uuid)
        if document is None or document.deleted_at is not None:
            return {"status": "skipped", "reason": "document_not_found"}
        if document.mime_type != _PDF:
            return {"status": "skipped", "reason": "not_pdf"}

        file_path = absolute_storage_path(settings, document.storage_path)
        parsed = parse_document_file(file_path, document.mime_type, settings)
        upload_root = resolve_upload_root(settings)
        enriched = enrich_parsed_with_ocr(
            parsed,
            file_path,
            settings,
            upload_root=upload_root,
        )
        return {
            "status": "ok",
            "document_id": document_id,
            "ocr_pages_processed": enriched.metadata.get("ocr_pages_processed", 0),
            "char_count": len(enriched.full_text),
        }
    except (RecoverableParserError, ParserError) as e:
        logger.warning("OCR falló para documento %s: %s", document_id, e)
        return {"status": "error", "code": getattr(e, "code", "ocr_error"), "message": str(e)}
    finally:
        session.close()
