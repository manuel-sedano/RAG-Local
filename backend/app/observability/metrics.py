"""Registro central de métricas Prometheus para API, ingesta, retrieval y chat."""

from __future__ import annotations

import hashlib
import re
import uuid
from typing import Literal

from prometheus_client import Counter, Histogram

# Histogramas de latencia HTTP (segundos).
HTTP_REQUEST_DURATION = Histogram(
    "rag_http_request_duration_seconds",
    "Duración de peticiones HTTP",
    labelnames=("method", "endpoint", "status"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

HTTP_REQUESTS_TOTAL = Counter(
    "rag_http_requests_total",
    "Total de peticiones HTTP",
    labelnames=("method", "endpoint", "status"),
)

# Ingesta (worker Celery).
INGEST_STAGE_DURATION = Histogram(
    "rag_ingest_stage_duration_seconds",
    "Duración por etapa del pipeline de ingesta",
    labelnames=("stage", "status"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 15.0, 30.0, 60.0, 120.0, 300.0),
)

INGEST_DOCUMENTS_TOTAL = Counter(
    "rag_ingest_documents_total",
    "Documentos procesados por el worker de ingesta",
    labelnames=("status",),
)

EMBEDDINGS_PROCESSED_TOTAL = Counter(
    "rag_embeddings_processed_total",
    "Chunks embedidos durante la ingesta",
    labelnames=("status",),
)

# Retrieval.
RETRIEVAL_DURATION = Histogram(
    "rag_retrieval_duration_seconds",
    "Duración de sub-etapas de retrieval",
    labelnames=("type", "status"),
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Chat / generación RAG.
CHAT_GENERATION_DURATION = Histogram(
    "rag_chat_generation_duration_seconds",
    "Duración de fases de generación de chat",
    labelnames=("phase", "status"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 15.0, 30.0, 60.0, 120.0),
)

CHAT_MESSAGES_TOTAL = Counter(
    "rag_chat_messages_total",
    "Mensajes de chat generados",
    labelnames=("mode", "status"),
)

_UUID_IN_PATH = re.compile(
    r"/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def normalize_endpoint(path: str) -> str:
    """Reduce cardinalidad reemplazando UUIDs en rutas."""
    normalized = _UUID_IN_PATH.sub("/{id}", path.split("?")[0].rstrip("/") or "/")
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized


def kb_label(kb_id: uuid.UUID | str | None, *, include_kb_id: bool) -> str:
    """Etiqueta de KB: vacía por defecto (privacidad) o hash corto si está habilitado."""
    if not include_kb_id or kb_id is None:
        return ""
    raw = str(kb_id)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:8]
    return digest


def observe_http_request(*, method: str, endpoint: str, status: int, duration_s: float) -> None:
    status_label = str(status)
    HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint, status=status_label).observe(
        duration_s
    )
    HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=status_label).inc()


def observe_ingest_stage(stage: str, duration_s: float, *, status: str = "ok") -> None:
    INGEST_STAGE_DURATION.labels(stage=stage, status=status).observe(duration_s)


def record_ingest_outcome(status: Literal["succeeded", "failed", "quarantined", "skipped"]) -> None:
    INGEST_DOCUMENTS_TOTAL.labels(status=status).inc()


def record_embeddings_processed(count: int, *, status: str = "ok") -> None:
    if count > 0:
        EMBEDDINGS_PROCESSED_TOTAL.labels(status=status).inc(count)


def observe_retrieval(retrieval_type: str, duration_s: float, *, status: str = "ok") -> None:
    RETRIEVAL_DURATION.labels(type=retrieval_type, status=status).observe(duration_s)


def observe_chat_phase(phase: str, duration_s: float, *, status: str = "ok") -> None:
    CHAT_GENERATION_DURATION.labels(phase=phase, status=status).observe(duration_s)


def record_chat_message(*, mode: Literal["sync", "stream"], status: str = "ok") -> None:
    CHAT_MESSAGES_TOTAL.labels(mode=mode, status=status).inc()
