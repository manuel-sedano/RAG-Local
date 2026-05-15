"""Instancia de Celery y configuración de colas del worker de ingesta.

Este módulo se importa tanto desde el worker (entrypoint Celery)
como desde otros módulos que quieran encolar tareas (`celery_app`).
"""

from __future__ import annotations

from celery import Celery
from kombu import Queue

from app.core.config import get_settings


def create_celery_app() -> Celery:
    settings = get_settings()

    app = Celery("rag_local_worker")

    # Broker / backend
    app.conf.broker_url = settings.resolved_celery_broker_url
    app.conf.result_backend = settings.resolved_celery_result_backend

    # En tests forzamos ejecución síncrona (sin worker externo).
    app.conf.task_always_eager = settings.celery_task_always_eager

    # Colas dedicadas por tipo de trabajo.
    app.conf.task_queues = (
        Queue("ingest"),
        Queue("ocr"),
        Queue("embed"),
    )

    # Rutas por prefijo de tarea.
    app.conf.task_routes = {
        "app.tasks.ingest.*": {"queue": "ingest"},
        "app.tasks.ocr.*": {"queue": "ocr"},
        "app.tasks.embed.*": {"queue": "embed"},
    }

    # Descubrir tareas dentro del paquete `app.tasks`.
    app.autodiscover_tasks(["app.tasks"])

    return app


celery_app = create_celery_app()

