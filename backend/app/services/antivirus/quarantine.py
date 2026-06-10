"""Cuarentena de documentos infectados."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.document import Document
from app.services.auth_audit import log_security_event
from app.services.document_service import QUARANTINED, absolute_storage_path, resolve_upload_root

logger = logging.getLogger(__name__)


def _quarantine_relative_path(document: Document, src: Path) -> str:
    ext = src.suffix or ".bin"
    return f"quarantine/{document.kb_id}/{document.id}{ext}"


def quarantine_infected_document(
    session: Session,
    settings: Settings,
    document: Document,
    *,
    signature: str,
    raw_response: str,
    engine: str | None,
) -> str:
    """Mueve el binario a `uploads/quarantine/` y marca el documento."""
    root = resolve_upload_root(settings)
    src = absolute_storage_path(settings, document.storage_path)
    if not src.is_file():
        msg = "No se encontró el archivo a poner en cuarentena."
        raise FileNotFoundError(msg)

    rel = _quarantine_relative_path(document, src)
    dest = (root / rel).resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    shutil.move(str(src), str(dest))

    document.storage_path = rel
    document.status = QUARANTINED
    document.error_code = "MALWARE_DETECTED"
    document.error_message = (
        f"Se detectó software malicioso ({signature}). El archivo está en cuarentena."
    )

    log_security_event(
        session,
        kind="DOCUMENT_QUARANTINED",
        user_id=document.uploaded_by_user_id,
        ip_address=None,
        details={
            "kb_id": str(document.kb_id),
            "document_id": str(document.id),
            "sha256": document.sha256,
            "signature": signature,
            "engine": engine,
            "raw_response": (raw_response or "")[:2000],
            "quarantine_path": rel,
        },
    )
    session.add(document)
    session.flush()

    logger.warning(
        "Documento %s en cuarentena (kb=%s, firma=%s)",
        document.id,
        document.kb_id,
        signature,
    )
    return rel
