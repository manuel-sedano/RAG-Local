"""Serialización de citas para API REST y eventos Socket.IO."""

from __future__ import annotations

import uuid
from typing import Any

from app.models.chat import MessageCitation
from app.services.chat_paths import build_file_path, build_viewer_path


def citation_to_dict(kb_id: uuid.UUID, citation: MessageCitation) -> dict[str, Any]:
    doc = citation.document
    if doc is None:
        msg = f"Documento {citation.document_id} no disponible para la cita."
        raise ValueError(msg)
    return {
        "document_id": str(citation.document_id),
        "chunk_id": str(citation.chunk_id),
        "filename_original": doc.filename_original,
        "mime_type": doc.mime_type,
        "page_start": citation.page_start,
        "page_end": citation.page_end,
        "score": citation.score,
        "viewer_path": build_viewer_path(
            kb_id,
            citation.document_id,
            page_start=citation.page_start,
        ),
        "file_path": build_file_path(kb_id, citation.document_id),
    }
