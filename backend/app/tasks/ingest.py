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


def _pipeline_ingest_document(session: Session, document: Document) -> dict[str, Any]:
    """Ejecuta el pipeline de ingesta por etapas.

    De momento las etapas son stubs que solo miden tiempos; la lógica
    real de parse/OCR/chunk/embed/qdrant se implementará en otras
    features, pero la forma general se mantiene.
    """

    metrics: dict[str, Any] = {}

    def _stage(name: str, fn) -> None:
        start = time.perf_counter()
        fn()
        elapsed_ms = (time.perf_counter() - start) * 1000
        metrics[f"ingest_{name}_ms"] = round(elapsed_ms, 2)

    settings = get_settings()

    def antivirus() -> None:
        if not settings.environment:
            raise IngestionError("invalid_environment")
        time.sleep(0)  # placeholder ligero

    def parse() -> None:
        time.sleep(0)

    def ocr() -> None:
        time.sleep(0)

    def normalize() -> None:
        time.sleep(0)

    def chunk() -> None:
        # MVP: no generamos chunks reales aún, pero dejamos el contador
        # preparado para no romper código que lo consulte.
        if document.chunk_count is None:
            document.chunk_count = 0

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

    # Información mínima de trazabilidad.
    metrics["document_id"] = str(document.id)
    metrics["kb_id"] = str(document.kb_id)

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
