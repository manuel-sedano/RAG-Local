"""Instancia Celery (broker/result desde settings)."""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

_s = get_settings()
_celery_kwargs: dict[str, str] = {"broker": _s.resolved_celery_broker_url}
_rb = _s.resolved_celery_result_backend
if _rb:
    _celery_kwargs["backend"] = _rb

celery_app = Celery("rag_local", **_celery_kwargs)
celery_app.conf.task_always_eager = _s.celery_task_always_eager
celery_app.conf.task_eager_propagates = True

import app.tasks.ingest  # noqa: E402, F401 — registra `ingest_document`
