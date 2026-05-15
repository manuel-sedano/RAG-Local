"""Tareas asíncronas (Celery / colas)."""

from app.tasks.embed import embed_document_chunks_task
from app.tasks.ingest import ingest_document

__all__ = ["ingest_document", "embed_document_chunks_task"]
