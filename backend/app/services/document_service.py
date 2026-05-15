"""CRUD de documentos, almacenamiento en disco y cola de ingesta."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.document import Document
from app.models.user import User
from app.services.auth_audit import log_security_event
from app.services.upload_media import extension_for_mime, magic_matches_declared_mime

# Estados persistidos en `documents.status`
UPLOADED = "UPLOADED"
PROCESSING = "PROCESSING"
READY = "READY"
FAILED = "FAILED"
QUARANTINED = "QUARANTINED"
DELETED = "DELETED"


def resolve_upload_root(settings: Settings) -> Path:
    raw = (settings.upload_storage_dir or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    # backend/app/services → parents[3] = raíz del repo
    return Path(__file__).resolve().parents[3] / "uploads"


def safe_filename_original(name: str | None) -> str:
    if not name or not str(name).strip():
        return "upload.bin"
    base = os.path.basename(str(name).strip())
    base = base.replace("\x00", "")
    if not base or base in (".", ".."):
        return "upload.bin"
    return base[:512]


def parse_tags_field(raw: str | None) -> list[str] | dict[str, Any] | None:
    if raw is None or not str(raw).strip():
        return None
    s = str(raw).strip()
    if s.startswith("["):
        try:
            data = json.loads(s)
        except json.JSONDecodeError:
            msg = "El campo tags no es un JSON válido."
            raise ValueError(msg) from None
        if isinstance(data, list):
            return [str(x) for x in data]
        if isinstance(data, dict):
            return data
        msg = "tags debe ser un array JSON o un objeto JSON."
        raise ValueError(msg)
    return [p.strip() for p in s.split(",") if p.strip()]


def _assert_path_under_root(root: Path, candidate: Path) -> None:
    root_r = root.resolve()
    cand_r = candidate.resolve()
    if root_r not in cand_r.parents and cand_r != root_r:
        msg = "Ruta de almacenamiento inválida."
        raise ValueError(msg)


def absolute_storage_path(settings: Settings, storage_path: str) -> Path:
    root = resolve_upload_root(settings)
    full = (root / storage_path).resolve()
    _assert_path_under_root(root, full)
    return full


def find_duplicate_sha256(db: Session, *, kb_id: uuid.UUID, sha256: str) -> Document | None:
    q = select(Document).where(
        Document.kb_id == kb_id,
        Document.sha256 == sha256,
        Document.deleted_at.is_(None),
    )
    return db.execute(q).scalar_one_or_none()


async def save_upload_stream(
    *,
    settings: Settings,
    kb_id: uuid.UUID,
    declared_mime: str,
    file_obj: Any,
    max_bytes: int,
) -> tuple[Path, str, int, str]:
    """Escribe el archivo bajo el root de uploads; devuelve (ruta absoluta, storage_path relativo, size, sha256)."""
    ext = extension_for_mime(declared_mime)
    if not ext:
        msg = "Extensión desconocida para el MIME declarado."
        raise ValueError(msg)

    file_uuid = uuid.uuid4()
    rel_dir = f"{kb_id}"
    rel_path = f"{rel_dir}/{file_uuid}{ext}"
    root = resolve_upload_root(settings)
    dest = (root / rel_path).resolve()
    _assert_path_under_root(root, dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    h = hashlib.sha256()
    total = 0
    head = b""
    head_limit = 65536

    tmp_path = dest.with_suffix(dest.suffix + ".part")
    try:
        with open(tmp_path, "wb") as out:
            while True:
                chunk = await file_obj.read(1024 * 1024)
                if not chunk:
                    break
                if total == 0:
                    head = chunk[:head_limit]
                elif len(head) < head_limit and total < head_limit:
                    need = head_limit - len(head)
                    head += chunk[:need]

                total += len(chunk)
                if total > max_bytes:
                    msg = "UPLOAD_TOO_LARGE"
                    raise ValueError(msg)
                h.update(chunk)
                out.write(chunk)

        if total == 0:
            msg = "El archivo está vacío."
            raise ValueError(msg)

        if not magic_matches_declared_mime(declared_mime=declared_mime, head=head):
            msg = "UPLOAD_INVALID_TYPE"
            raise ValueError(msg)

        os.replace(tmp_path, dest)
    except Exception:
        if tmp_path.is_file():
            tmp_path.unlink(missing_ok=True)
        raise

    return dest, rel_path, total, h.hexdigest()


def create_document_after_upload(
    db: Session,
    settings: Settings,
    *,
    kb_id: uuid.UUID,
    user: User,
    filename_original: str,
    storage_rel_path: str,
    mime_type: str,
    size_bytes: int,
    sha256: str,
    tags: list[str] | dict[str, Any] | None,
    source: str | None,
    language: str | None,
    ip_address: str | None,
) -> Document:
    if find_duplicate_sha256(db, kb_id=kb_id, sha256=sha256):
        msg = "DUPLICATE_DOCUMENT"
        raise ValueError(msg)

    doc = Document(
        kb_id=kb_id,
        uploaded_by_user_id=user.id,
        filename_original=filename_original,
        storage_path=storage_rel_path,
        mime_type=mime_type,
        size_bytes=size_bytes,
        sha256=sha256,
        language=language,
        source=source,
        tags=tags,
        status=UPLOADED,
    )
    db.add(doc)
    db.flush()
    log_security_event(
        db,
        kind="DOCUMENT_UPLOADED",
        user_id=user.id,
        ip_address=ip_address,
        details={
            "kb_id": str(kb_id),
            "document_id": str(doc.id),
            "mime_type": mime_type,
            "size_bytes": size_bytes,
        },
    )
    return doc


def list_documents(
    db: Session,
    *,
    kb_id: uuid.UUID,
    status: str | None,
    limit: int,
    cursor: uuid.UUID | None,
) -> tuple[list[Document], uuid.UUID | None]:
    lim = max(1, min(limit, 100))
    q = select(Document).where(
        Document.kb_id == kb_id,
        Document.deleted_at.is_(None),
    )
    if status:
        q = q.where(Document.status == status)
    if cursor is not None:
        cur = db.get(Document, cursor)
        if cur is None or cur.kb_id != kb_id:
            msg = "CURSOR_INVALID"
            raise ValueError(msg)
        q = q.where(
            or_(
                Document.created_at < cur.created_at,
                and_(Document.created_at == cur.created_at, Document.id < cur.id),
            )
        )
    q = q.order_by(Document.created_at.desc(), Document.id.desc()).limit(lim + 1)
    rows = list(db.execute(q).scalars().all())
    next_cursor: uuid.UUID | None = None
    if len(rows) > lim:
        rows = rows[:lim]
        next_cursor = rows[-1].id
    return rows, next_cursor


def get_document_for_kb(db: Session, *, kb_id: uuid.UUID, doc_id: uuid.UUID) -> Document | None:
    doc = db.get(Document, doc_id)
    if doc is None or doc.kb_id != kb_id or doc.deleted_at is not None:
        return None
    return doc


def soft_delete_document(
    db: Session,
    *,
    doc: Document,
    user: User,
    ip_address: str | None,
) -> None:
    doc.deleted_at = datetime.now(UTC)
    doc.status = DELETED
    db.flush()
    log_security_event(
        db,
        kind="DOCUMENT_DELETED",
        user_id=user.id,
        ip_address=ip_address,
        details={"kb_id": str(doc.kb_id), "document_id": str(doc.id)},
    )


def status_payload(doc: Document) -> dict[str, Any]:
    """Respuesta de `/status` hasta que el worker rellene métricas reales."""
    err = None
    if doc.error_code:
        err = {"code": doc.error_code, "message": doc.error_message}
    pending = {"status": "PENDING", "duration_ms": 0}
    done = {"status": "DONE", "duration_ms": 0}
    skipped = {"status": "SKIPPED", "duration_ms": 0}
    if doc.status == UPLOADED:
        stages = {
            "antivirus": pending,
            "parse": pending,
            "ocr": pending,
            "normalize": pending,
            "chunk": pending,
            "embed": pending,
            "qdrant_upsert": pending,
        }
    elif doc.status == PROCESSING:
        stages = {
            "antivirus": done,
            "parse": done,
            "ocr": skipped,
            "normalize": pending,
            "chunk": pending,
            "embed": pending,
            "qdrant_upsert": pending,
        }
    elif doc.status == READY:
        stages = {
            "antivirus": done,
            "parse": done,
            "ocr": skipped,
            "normalize": done,
            "chunk": done,
            "embed": done,
            "qdrant_upsert": done,
        }
    elif doc.status in (FAILED, QUARANTINED):
        stages = {
            "antivirus": done,
            "parse": pending,
            "ocr": skipped,
            "normalize": pending,
            "chunk": pending,
            "embed": pending,
            "qdrant_upsert": pending,
        }
    else:
        stages = {k: pending for k in ("antivirus", "parse", "ocr", "normalize", "chunk", "embed", "qdrant_upsert")}

    return {
        "document_id": str(doc.id),
        "status": doc.status,
        "stages": stages,
        "error": err,
    }


def disposition_from_query(disposition: str | None, mime_type: str) -> str:
    if disposition in ("inline", "attachment"):
        return disposition
    if mime_type == "application/pdf" or mime_type.startswith("text/"):
        return "inline"
    return "attachment"


def ascii_fallback_filename(name: str) -> str:
    out = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "document"
    return out[:200]
