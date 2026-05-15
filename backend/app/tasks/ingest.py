"""Tareas de ingesta de documentos."""

from __future__ import annotations

import logging

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="ingest_document", ignore_result=True)
def ingest_document(document_id: str) -> None:
    """Encolado tras upload; implementación completa en `feat/ingestion-worker`."""
    logger.info("ingest_document encolado (stub): document_id=%s", document_id)
