"""Tests del worker de ingesta (Celery) y endpoint reindex.

Integración: requiere TEST_DATABASE_URL (misma convención que auth/KB).
En ENVIRONMENT=test Celery corre en modo eager (sin worker externo).
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import fitz
import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import clear_settings_cache, get_settings
from app.models.document import Chunk, Document, DocumentIngestionRun
from app.models.knowledge_base import KbMembership, KnowledgeBase
from app.models.user import User
from app.services.passwords import hash_password
from app.tasks import ingest as ingest_module
from app.tasks.ingest import (
    BASE_BACKOFF_SECONDS,
    MAX_INGEST_ATTEMPTS,
    IngestionError,
    _compute_backoff,
    _is_already_ingested,
    ingest_document,
)
from tests.test_auth_integration import (
    _alembic_config,
    _ensure_database_exists,
    _reset_public_schema,
)


def test_compute_backoff_exponential_and_capped() -> None:
    assert _compute_backoff(1) == BASE_BACKOFF_SECONDS
    assert _compute_backoff(2) == BASE_BACKOFF_SECONDS * 2
    assert _compute_backoff(3) == BASE_BACKOFF_SECONDS * 4
    assert _compute_backoff(20) == 10 * 60


def test_is_already_ingested_requires_ready_and_chunks() -> None:
    doc = SimpleNamespace(status="READY", chunks=[])
    assert _is_already_ingested(doc) is False

    doc.chunks = [object()]
    assert _is_already_ingested(doc) is True

    doc.status = "PROCESSING"
    assert _is_already_ingested(doc) is False


def test_celery_ingest_queues_and_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    clear_settings_cache()
    from app.tasks.celery_app import create_celery_app

    app = create_celery_app()
    queue_names = {q.name for q in app.conf.task_queues}
    assert queue_names == {"ingest", "ocr", "embed"}
    assert app.conf.task_routes["app.tasks.ingest.*"]["queue"] == "ingest"
    assert app.conf.task_routes["app.tasks.embed.*"]["queue"] == "embed"
    assert app.conf.task_always_eager is True


@pytest.fixture(scope="module")
def ingest_postgres_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("Define TEST_DATABASE_URL para pruebas de ingesta.")
    _ensure_database_exists(url)
    _reset_public_schema(url)
    cfg = _alembic_config(url)
    command.upgrade(cfg, "head")
    return url


def _write_minimal_pdf(path: Path, text: str = "Texto de prueba para ingesta.") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


@pytest.fixture
def ingest_db(
    ingest_postgres_url: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[sessionmaker[Session], str, str, str, uuid.UUID, uuid.UUID]:
    upload_root = tmp_path / "ingest_uploads"
    upload_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DATABASE_URL", ingest_postgres_url)
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("UPLOAD_STORAGE_DIR", str(upload_root))
    monkeypatch.setenv("QDRANT_ENABLED", "false")
    clear_settings_cache()
    settings = get_settings()
    engine = create_engine(ingest_postgres_url)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    pwd = "ingest-integration-9ch"
    email = f"ingest_{uuid.uuid4().hex[:10]}@example.com"
    with SessionLocal() as db:
        user = User(
            email=email,
            password_hash=hash_password(pwd, pepper=settings.password_pepper),
            role="user",
            is_active=True,
        )
        db.add(user)
        db.flush()
        kb = KnowledgeBase(name="KB ingest test", owner_user_id=user.id)
        db.add(kb)
        db.flush()
        db.add(KbMembership(kb_id=kb.id, user_id=user.id, role="owner"))
        storage_rel = f"{kb.id}/sample.pdf"
        doc = Document(
            kb_id=kb.id,
            uploaded_by_user_id=user.id,
            filename_original="sample.pdf",
            storage_path=storage_rel,
            mime_type="application/pdf",
            size_bytes=128,
            sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            status="UPLOADED",
        )
        db.add(doc)
        db.commit()
        _write_minimal_pdf(upload_root / storage_rel)
        kb_id = kb.id
        doc_id = doc.id
    engine.dispose()
    yield SessionLocal, email, pwd, ingest_postgres_url, kb_id, doc_id
    clear_settings_cache()


def _reload_document(SessionLocal: sessionmaker[Session], doc_id: uuid.UUID) -> Document:
    with SessionLocal() as db:
        doc = db.get(Document, doc_id)
        assert doc is not None
        _ = doc.ingestion_runs
        _ = doc.chunks
        db.expunge(doc)
        return doc


def test_ingest_success_state_transition(ingest_db: tuple) -> None:
    SessionLocal, _email, _pwd, _url, _kb_id, doc_id = ingest_db

    ingest_document.run(str(doc_id))

    doc = _reload_document(SessionLocal, doc_id)
    assert doc.status == "READY"
    assert doc.error_code is None
    assert len(doc.ingestion_runs) == 1
    run = doc.ingestion_runs[0]
    assert run.status == "SUCCEEDED"
    assert run.attempt == 1
    assert run.metrics is not None
    assert "ingest_parse_ms" in run.metrics
    assert run.metrics["document_id"] == str(doc_id)
    assert run.metrics.get("parse_parser") == "pymupdf"
    assert doc.page_count is not None and doc.page_count >= 1
    assert run.metrics.get("chunk_count", 0) >= 1
    assert "chunking_config_hash" in run.metrics
    assert len(doc.chunks) == doc.chunk_count
    assert doc.chunks[0].embedding_model == "bge-m3"
    assert doc.chunks[0].qdrant_point_id == str(doc.chunks[0].id)
    assert doc.chunks[0].chunk_metadata is not None
    assert "chunking_config_hash" in doc.chunks[0].chunk_metadata
    assert doc.chunks[0].chunk_metadata.get("embedding_dim")
    assert run.metrics.get("embedding_status") == "done"
    assert run.metrics.get("embedding_count", 0) >= 1
    assert run.metrics.get("qdrant_status") == "skipped"


def test_ingest_idempotent_when_ready_with_chunks(ingest_db: tuple) -> None:
    SessionLocal, _email, _pwd, _url, kb_id, doc_id = ingest_db

    with SessionLocal() as db:
        doc = db.get(Document, doc_id)
        assert doc is not None
        doc.status = "READY"
        db.add(
            Chunk(
                document_id=doc.id,
                kb_id=kb_id,
                chunk_index=0,
                text="fragmento",
                embedding_model="bge-m3",
            )
        )
        db.commit()

    ingest_document.run(str(doc_id))

    doc = _reload_document(SessionLocal, doc_id)
    assert doc.status == "READY"
    assert len(doc.ingestion_runs) == 0


def test_ingest_controlled_error_marks_failed(
    ingest_db: tuple,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    SessionLocal, _email, _pwd, _url, _kb_id, doc_id = ingest_db
    # Sin reintento Celery: tras el primer fallo attempt (1) no es < MAX (1).
    monkeypatch.setattr(ingest_module, "MAX_INGEST_ATTEMPTS", 1)

    def _fail_pipeline(_session: Session, _document: Document) -> dict[str, Any]:
        raise IngestionError("parse_fail")

    monkeypatch.setattr(ingest_module, "_pipeline_ingest_document", _fail_pipeline)

    ingest_document.run(str(doc_id))

    doc = _reload_document(SessionLocal, doc_id)
    assert doc.status == "FAILED"
    assert doc.error_code == "ingestion_error"
    assert doc.error_message == "parse_fail"
    assert len(doc.ingestion_runs) == 1
    assert doc.ingestion_runs[0].status == "FAILED"
    assert doc.ingestion_runs[0].error_code == "ingestion_error"


def test_ingest_max_attempts_exceeded_without_pipeline(ingest_db: tuple) -> None:
    SessionLocal, _email, _pwd, _url, _kb_id, doc_id = ingest_db

    with SessionLocal() as db:
        for attempt in range(1, MAX_INGEST_ATTEMPTS + 1):
            db.add(
                DocumentIngestionRun(
                    document_id=doc_id,
                    attempt=attempt,
                    status="FAILED",
                    error_code="ingestion_error",
                    error_message="prev",
                )
            )
        db.commit()

    ingest_document.run(str(doc_id))

    doc = _reload_document(SessionLocal, doc_id)
    assert doc.status == "FAILED"
    assert doc.error_code == "max_retries_exceeded"
    runs = sorted(doc.ingestion_runs, key=lambda r: r.attempt)
    assert runs[-1].attempt == MAX_INGEST_ATTEMPTS + 1
    assert runs[-1].status == "FAILED"
    assert runs[-1].error_code == "max_retries_exceeded"


def test_ingest_retries_increment_attempt_on_repeated_failures(
    ingest_db: tuple,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    SessionLocal, _email, _pwd, _url, _kb_id, doc_id = ingest_db
    expected_attempts = MAX_INGEST_ATTEMPTS
    monkeypatch.setattr(ingest_module, "MAX_INGEST_ATTEMPTS", 1)

    def _fail_pipeline(_session: Session, _document: Document) -> dict[str, Any]:
        raise IngestionError("stage_fail")

    monkeypatch.setattr(ingest_module, "_pipeline_ingest_document", _fail_pipeline)

    for _ in range(expected_attempts):
        ingest_document.run(str(doc_id))

    doc = _reload_document(SessionLocal, doc_id)
    assert doc.status == "FAILED"
    assert len(doc.ingestion_runs) == expected_attempts
    assert {r.attempt for r in doc.ingestion_runs} == set(range(1, expected_attempts + 1))


def test_reindex_endpoint_enqueues_ingest(
    ingest_db: tuple,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    SessionLocal, email, pwd, postgres_url, kb_id, doc_id = ingest_db
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    clear_settings_cache()

    from app.main import app

    with TestClient(app) as client:
        token = client.post(
            "/api/auth/login",
            json={"email": email, "password": pwd},
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = client.post(
            f"/api/kbs/{kb_id}/documents/{doc_id}/reindex",
            headers=headers,
        )
        assert r.status_code == 202, r.text
        body = r.json()
        assert body["document_id"] == str(doc_id)
        assert "ingestion_job_id" in body

    doc = _reload_document(SessionLocal, doc_id)
    assert doc.status == "READY"
    assert any(run.status == "SUCCEEDED" for run in doc.ingestion_runs)


def test_reindex_endpoint_404_for_unknown_document(
    ingest_db: tuple,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _SessionLocal, email, pwd, postgres_url, kb_id, _doc_id = ingest_db
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    clear_settings_cache()

    from app.main import app

    unknown = uuid.uuid4()
    with TestClient(app) as client:
        token = client.post(
            "/api/auth/login",
            json={"email": email, "password": pwd},
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        r = client.post(
            f"/api/kbs/{kb_id}/documents/{unknown}/reindex",
            headers=headers,
        )
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"
