"""Tareas Celery de embeddings (cola `embed`)."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.session import get_engine
from app.models.document import Document
from app.services.embeddings import EmbeddingError, embed_document_chunks
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_session_factory() -> sessionmaker[Session]:
    engine = get_engine()
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


@celery_app.task(name="app.tasks.embed.embed_document_chunks")
def embed_document_chunks_task(document_id: str) -> dict:
    """Embedea todos los chunks de un documento (cola dedicada `embed`)."""
    session_factory = _get_session_factory()
    session = session_factory()
    settings = get_settings()

    try:
        doc_uuid = uuid.UUID(document_id)
        document = session.get(Document, doc_uuid)
        if document is None or document.deleted_at is not None:
            logger.warning("Documento %s no existe; omitiendo embeddings.", document_id)
            return {"embedding_status": "skipped", "reason": "document_missing"}

        metrics, _vectors = embed_document_chunks(session, document, settings)
        session.commit()
        logger.info("Embeddings de documento %s completados.", document_id)
        return metrics
    except EmbeddingError:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
