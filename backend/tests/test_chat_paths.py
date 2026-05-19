"""Rutas derivadas para citas (unitario, sin Postgres)."""

from __future__ import annotations

import uuid

from app.services.chat_paths import build_file_path, build_viewer_path


def test_build_viewer_and_file_paths() -> None:
    kb_id = uuid.UUID("00000000-0000-4000-8000-0000000000a1")
    doc_id = uuid.UUID("00000000-0000-4000-8000-0000000000b2")
    assert build_viewer_path(kb_id, doc_id) == (
        f"/kbs/{kb_id}/documents/{doc_id}"
    )
    assert build_viewer_path(kb_id, doc_id, page_start=3) == (
        f"/kbs/{kb_id}/documents/{doc_id}?page=3"
    )
    assert build_file_path(kb_id, doc_id) == (
        f"/api/kbs/{kb_id}/documents/{doc_id}/file"
    )
