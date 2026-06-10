"""Tests del endpoint /metrics y métricas instrumentadas."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import clear_settings_cache
from app.observability.metrics import (
    observe_ingest_stage,
    observe_retrieval,
    record_chat_message,
)


@pytest.fixture
def metrics_client() -> TestClient:
    os.environ["PROMETHEUS_ENABLED"] = "true"
    clear_settings_cache()
    from app.main import app

    with TestClient(app) as client:
        yield client
    clear_settings_cache()


def test_metrics_endpoint_returns_prometheus_text(metrics_client: TestClient) -> None:
    metrics_client.get("/api/health")
    response = metrics_client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    body = response.text
    assert "rag_http_requests_total" in body
    assert 'endpoint="/api/health"' in body or 'endpoint="/api/health"' in body.replace(" ", "")


def test_metrics_disabled_returns_404() -> None:
    os.environ["PROMETHEUS_ENABLED"] = "false"
    clear_settings_cache()
    from app.main import create_app

    with TestClient(create_app()) as client:
        response = client.get("/metrics")
    assert response.status_code == 404
    clear_settings_cache()


def test_ingest_and_retrieval_metrics_registered() -> None:
    observe_ingest_stage("parse", 0.12, status="ok")
    observe_retrieval("vector", 0.05, status="ok")
    record_chat_message(mode="sync", status="ok")

    os.environ["PROMETHEUS_ENABLED"] = "true"
    clear_settings_cache()
    from app.main import app

    with TestClient(app) as client:
        body = client.get("/metrics").text

    assert "rag_ingest_stage_duration_seconds" in body
    assert "rag_retrieval_duration_seconds" in body
    assert "rag_chat_messages_total" in body
    clear_settings_cache()
