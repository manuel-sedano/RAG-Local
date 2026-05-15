"""Persistencia opcional de artefactos de texto en disco."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def artifact_dir(upload_root: Path, kb_id: str, document_id: str) -> Path:
    return upload_root / kb_id / "artifacts" / document_id


def save_text_artifacts(
    upload_root: Path,
    *,
    kb_id: str,
    document_id: str,
    extracted_text: str,
    normalized_text: str,
) -> dict[str, Any]:
    base = artifact_dir(upload_root, kb_id, document_id)
    base.mkdir(parents=True, exist_ok=True)

    extracted_path = base / "extracted.txt"
    normalized_path = base / "normalized.txt"
    extracted_path.write_text(extracted_text, encoding="utf-8")
    normalized_path.write_text(normalized_text, encoding="utf-8")

    return {
        "extracted_path": str(extracted_path.relative_to(upload_root)),
        "normalized_path": str(normalized_path.relative_to(upload_root)),
        "extracted_sha256": hashlib.sha256(extracted_text.encode("utf-8")).hexdigest(),
        "normalized_sha256": hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
    }
