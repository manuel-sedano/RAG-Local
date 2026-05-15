"""Tareas asíncronas (Celery / colas)."""

from app.tasks.ingest import ingest_document

__all__ = ["ingest_document"]
