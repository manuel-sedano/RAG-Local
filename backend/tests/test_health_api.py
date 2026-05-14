"""Tests de rutas HTTP básicas."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.services.health_check import DependencyResult


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "rag-local-backend"
    assert "/api/health" in body["api"]


def test_health_ok_when_dependencies_up(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake(_settings):
        return [
            DependencyResult(name="postgres", ok=True, latency_ms=1.0),
            DependencyResult(name="redis", ok=True, latency_ms=1.0),
            DependencyResult(name="qdrant", ok=True, latency_ms=1.0),
            DependencyResult(name="ollama", ok=True, latency_ms=1.0),
        ]

    monkeypatch.setattr("app.api.routes.health.run_dependency_checks", _fake)
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["request_id"]
    assert all(dep["ok"] for dep in body["dependencies"].values())


def test_health_503_when_dependency_down(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake(_settings):
        return [
            DependencyResult(name="postgres", ok=True, latency_ms=1.0),
            DependencyResult(name="redis", ok=False, detail="boom"),
            DependencyResult(name="qdrant", ok=True, latency_ms=1.0),
            DependencyResult(name="ollama", ok=True, latency_ms=1.0),
        ]

    monkeypatch.setattr("app.api.routes.health.run_dependency_checks", _fake)
    response = client.get("/api/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["redis"]["ok"] is False


def test_request_id_header_roundtrip(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake(_settings):
        return [
            DependencyResult(name="postgres", ok=True, latency_ms=1.0),
            DependencyResult(name="redis", ok=True, latency_ms=1.0),
            DependencyResult(name="qdrant", ok=True, latency_ms=1.0),
            DependencyResult(name="ollama", ok=True, latency_ms=1.0),
        ]

    monkeypatch.setattr("app.api.routes.health.run_dependency_checks", _fake)
    response = client.get("/api/health", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Request-ID"] == "abc-123"
    assert response.json()["request_id"] == "abc-123"
