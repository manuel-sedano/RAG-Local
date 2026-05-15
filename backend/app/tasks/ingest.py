"""Tareas de ingesta de documentos.

MVP: orquesta un pipeline por etapas sobre un documento ya subido,
crea registros `DocumentIngestionRun` y actualiza el estado del
`Document`. Las etapas de antivirus/parse/OCR/chunk/embed/qdrant son
stubs que se rellenarán en las features siguientes, pero la estructura
de colas, reintentos e idempotencia ya queda lista.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from celery import Task
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.session import get_engine
from app.models.document import Document, DocumentIngestionRun
from app.services.document_service import absolute_storage_path, resolve_upload_root
from app.services.chunking import chunk_normalized_text, chunking_config_hash, persist_document_chunks
from app.services.parsing.artifacts import save_text_artifacts
from app.services.parsing.errors import ParserError, RecoverableParserError
from app.services.parsing.ocr import document_needs_ocr, enrich_parsed_with_ocr
from app.services.parsing.orchestrator import parse_document_file
from app.services.parsing.pipeline_context import IngestPipelineContext
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


# Reintentos y backoff
MAX_INGEST_ATTEMPTS = 3
BASE_BACKOFF_SECONDS = 10


def _get_session_factory() -> sessionmaker[Session]:
    engine = get_engine()
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


class IngestionError(Exception):
    """Error controlado de una etapa del pipeline de ingesta."""


def _compute_backoff(attempt: int) -> int:
    # Backoff exponencial sencillo, acotado.
    return min(BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)), 10 * 60)


def _start_ingestion_run(session: Session, document: Document) -> DocumentIngestionRun:
    last_attempt = 0
    if document.ingestion_runs:
        last_attempt = max(run.attempt for run in document.ingestion_runs)

    attempt = last_attempt + 1
    run = DocumentIngestionRun(
        document_id=document.id,
        attempt=attempt,
        status="RUNNING",
        metrics={},
    )
    document.status = "PROCESSING"
    document.error_code = None
    document.error_message = None
    session.add(run)
    session.add(document)
    session.commit()
    session.refresh(run)
    return run


def _mark_run_failed(
    session: Session,
    document: Document,
    run: DocumentIngestionRun,
    error_code: str,
    error_message: str,
) -> None:
    run.status = "FAILED"
    run.error_code = error_code
    run.error_message = error_message
    run.finished_at = run.finished_at or run.started_at
    document.status = "FAILED"
    document.error_code = error_code
    document.error_message = error_message
    session.add(run)
    session.add(document)
    session.commit()


def _mark_run_succeeded(
    session: Session,
    document: Document,
    run: DocumentIngestionRun,
    metrics: dict[str, Any],
) -> None:
    run.status = "SUCCEEDED"
    run.metrics = metrics
    run.finished_at = run.finished_at or run.started_at
    document.status = "READY"
    document.error_code = None
    document.error_message = None
    session.add(run)
    session.add(document)
    session.commit()


def _is_already_ingested(document: Document) -> bool:
    return document.status == "READY" and bool(document.chunks)


def _map_parser_error(exc: ParserError) -> IngestionError:
    if isinstance(exc, RecoverableParserError):
        return IngestionError(exc.code)
    return IngestionError(exc.code)


def _pipeline_ingest_document(session: Session, document: Document) -> dict[str, Any]:
    """Ejecuta el pipeline de ingesta por etapas."""

    metrics: dict[str, Any] = {}
    ctx = IngestPipelineContext()
    settings = get_settings()

    def _stage(name: str, fn) -> None:
        start = time.perf_counter()
        fn()
        elapsed_ms = (time.perf_counter() - start) * 1000
        metrics[f"ingest_{name}_ms"] = round(elapsed_ms, 2)

    def antivirus() -> None:
        if not settings.environment:
            raise IngestionError("invalid_environment")
        time.sleep(0)  # placeholder: ClamAV en feat/security-clamav

    def parse() -> None:
        file_path = absolute_storage_path(settings, document.storage_path)
        try:
            parsed = parse_document_file(file_path, document.mime_type, settings)
        except ParserError as e:
            raise _map_parser_error(e) from e
        ctx.parsed = parsed
        document.page_count = parsed.page_count or None
        session.add(document)
        metrics["parse_parser"] = parsed.parser_used
        metrics["parse_page_count"] = parsed.page_count
        metrics["parse_char_count"] = len(parsed.full_text)
        metrics["parse_needs_ocr"] = parsed.needs_ocr
        if parsed.encoding:
            metrics["parse_encoding"] = parsed.encoding

    def ocr() -> None:
        if ctx.parsed is None:
            metrics["ocr_status"] = "skipped"
            return
        if not settings.ocr_enabled:
            metrics["ocr_status"] = "disabled"
            return
        if ctx.parsed.mime_type != "application/pdf":
            metrics["ocr_status"] = "skipped"
            return
        if not document_needs_ocr(ctx.parsed, settings.ocr_min_chars_per_page):
            metrics["ocr_status"] = "skipped"
            return
        file_path = absolute_storage_path(settings, document.storage_path)
        try:
            ctx.parsed = enrich_parsed_with_ocr(
                ctx.parsed,
                file_path,
                settings,
                upload_root=resolve_upload_root(settings),
            )
        except ParserError as e:
            raise _map_parser_error(e) from e
        metrics["ocr_status"] = "done"
        metrics["ocr_pages_processed"] = ctx.parsed.metadata.get("ocr_pages_processed", 0)
        metrics["parse_char_count"] = len(ctx.parsed.full_text)

    def normalize() -> None:
        if ctx.parsed is None:
            raise IngestionError("parse_missing")
        ctx.normalized_text = ctx.parsed.full_text
        if settings.parser_save_artifacts:
            upload_root = resolve_upload_root(settings)
            ctx.artifact_paths = save_text_artifacts(
                upload_root,
                kb_id=str(document.kb_id),
                document_id=str(document.id),
                extracted_text=ctx.parsed.full_text,
                normalized_text=ctx.normalized_text,
            )
            metrics["artifacts"] = ctx.artifact_paths

    def chunk() -> None:
        if not ctx.normalized_text.strip():
            raise IngestionError("chunk_empty_text")
        ctx.chunks = chunk_normalized_text(
            ctx.normalized_text,
            settings,
            parsed=ctx.parsed,
        )
        if not ctx.chunks:
            raise IngestionError("chunk_no_segments")
        count = persist_document_chunks(session, document, ctx.chunks, settings)
        metrics["chunk_count"] = count
        metrics["chunking_config_hash"] = chunking_config_hash(settings)

    def embed() -> None:
        time.sleep(0)

    def qdrant_upsert() -> None:
        time.sleep(0)

    _stage("antivirus", antivirus)
    _stage("parse", parse)
    _stage("ocr", ocr)
    _stage("normalize", normalize)
    _stage("chunk", chunk)
    _stage("embed", embed)
    _stage("qdrant_upsert", qdrant_upsert)

    metrics["document_id"] = str(document.id)
    metrics["kb_id"] = str(document.kb_id)
    if ctx.parsed:
        metrics["parser_used"] = ctx.parsed.parser_used

    return metrics


@celery_app.task(bind=True, name="app.tasks.ingest.ingest_document")
def ingest_document(self: Task, document_id: str) -> None:
    """Tarea principal de ingesta de documentos.

    - Crea/actualiza `DocumentIngestionRun` por intento.
    - Aplica backoff exponencial hasta `MAX_INGEST_ATTEMPTS`.
    - Marca el `Document` en `FAILED` con `error_code` estable
      cuando se agotan los reintentos.
    - Es idempotente: si el documento ya está en `READY` y tiene
      chunks, no hace nada.
    """

    session_factory = _get_session_factory()
    session = session_factory()

    try:
        doc_uuid = uuid.UUID(document_id)
        document = session.get(Document, doc_uuid)
        if document is None or document.deleted_at is not None:
            logger.warning("Documento %s no existe o fue eliminado; nada que ingerir.", document_id)
            return

        if _is_already_ingested(document):
            logger.info(
                "Documento %s ya estaba ingerido (READY con chunks); se omite reindex automático.",
                document_id,
            )
            return

        run = _start_ingestion_run(session, document)

        if run.attempt > MAX_INGEST_ATTEMPTS:
            _mark_run_failed(
                session,
                document,
                run,
                error_code="max_retries_exceeded",
                error_message="Se alcanzó el número máximo de reintentos de ingesta.",
            )
            logger.error(
                "Documento %s alcanzó el máximo de intentos de ingesta (%s).",
                document_id,
                MAX_INGEST_ATTEMPTS,
            )
            return

        try:
            metrics = _pipeline_ingest_document(session, document)
            _mark_run_succeeded(session, document, run, metrics)
            logger.info("Ingesta de documento %s finalizada con éxito.", document_id)
        except IngestionError as e:
            # Errores controlados → reintento con backoff hasta el límite.
            backoff = _compute_backoff(run.attempt)
            _mark_run_failed(
                session,
                document,
                run,
                error_code="ingestion_error",
                error_message=str(e),
            )
            if run.attempt < MAX_INGEST_ATTEMPTS:
                logger.warning(
                    (
                        "Error de ingesta controlado para documento %s "
                        "(intento %s/%s). Reintento en %ss."
                    ),
                    document_id,
                    run.attempt,
                    MAX_INGEST_ATTEMPTS,
                    backoff,
                )
                raise self.retry(exc=e, countdown=backoff) from e
            logger.error(
                "Documento %s falló la ingesta tras %s intentos.",
                document_id,
                MAX_INGEST_ATTEMPTS,
            )
        except Exception as e:  # pragma: no cover - salvaguarda
            # Errores inesperados → se registran y también participan en el
            # mecanismo de reintentos, pero con un código distinto.
            backoff = _compute_backoff(run.attempt)
            _mark_run_failed(
                session,
                document,
                run,
                error_code="ingestion_unexpected_error",
                error_message=str(e),
            )
            if run.attempt < MAX_INGEST_ATTEMPTS:
                logger.exception(
                    "Error inesperado en ingesta de documento %s (intento %s/%s). "
                    "Reintento en %ss.",
                    document_id,
                    run.attempt,
                    MAX_INGEST_ATTEMPTS,
                    backoff,
                )
                raise self.retry(exc=e, countdown=backoff) from e
            logger.exception(
                "Documento %s falló la ingesta tras %s intentos por error inesperado.",
                document_id,
                MAX_INGEST_ATTEMPTS,
            )
    finally:
        session.close()
