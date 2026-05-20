"""Rutas derivadas en servidor para citas y visor (contrato `09-api-spec.md`)."""

from __future__ import annotations

import uuid


def build_viewer_path(
    kb_id: uuid.UUID,
    document_id: uuid.UUID,
    *,
    page_start: int | None = None,
) -> str:
    base = f"/kbs/{kb_id}/documents/{document_id}"
    if page_start is not None:
        return f"{base}?page={page_start}"
    return base


def build_file_path(kb_id: uuid.UUID, document_id: uuid.UUID) -> str:
    return f"/api/kbs/{kb_id}/documents/{document_id}/file"
