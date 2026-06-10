"""Tests de logging estructurado y correlación por IDs."""

from __future__ import annotations

import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.core.log_context import get_chat_id, get_document_id, get_kb_id, log_context
from app.core.logging_config import CorrelationFilter, JsonFormatter
from app.core.request_context import reset_request_id, set_request_id
from app.services.health_check import DependencyResult


def test_log_context_sets_and_resets_ids() -> None:
    assert get_document_id() is None
    with log_context(document_id="doc-1", chat_id="chat-2", kb_id="kb-3"):
        assert get_document_id() == "doc-1"
        assert get_chat_id() == "chat-2"
        assert get_kb_id() == "kb-3"
    assert get_document_id() is None
    assert get_chat_id() is None
    assert get_kb_id() is None


def test_json_formatter_includes_correlation_fields() -> None:
    token = set_request_id("req-test-1")
    try:
        with log_context(document_id="doc-abc", chat_id="chat-def", kb_id="kb-ghi"):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname=__file__,
                lineno=1,
                msg="evento de prueba",
                args=(),
                exc_info=None,
            )
            CorrelationFilter("rag-backend").filter(record)
            payload = json.loads(JsonFormatter().format(record))
    finally:
        reset_request_id(token)

    assert payload["request_id"] == "req-test-1"
    assert payload["document_id"] == "doc-abc"
    assert payload["chat_id"] == "chat-def"
    assert payload["kb_id"] == "kb-ghi"
    assert payload["service"] == "rag-backend"
    assert payload["message"] == "evento de prueba"


def test_correlation_middleware_from_kb_path(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="rag.access")

    async def _fake(_settings):
        return [
            DependencyResult(name="postgres", ok=True, latency_ms=1.0),
            DependencyResult(name="redis", ok=True, latency_ms=1.0),
            DependencyResult(name="qdrant", ok=True, latency_ms=1.0),
            DependencyResult(name="ollama", ok=True, latency_ms=1.0),
        ]

    monkeypatch.setattr("app.api.routes.health.run_dependency_checks", _fake)

    kb_id = "11111111-1111-4111-8111-111111111111"
    from app.main import app

    with TestClient(app) as client:
        root = logging.getLogger()
        if caplog.handler not in root.handlers:
            root.addHandler(caplog.handler)
        client.get(f"/api/kbs/{kb_id}/documents", headers={"Authorization": "Bearer invalid"})

    access_records = [r for r in caplog.records if r.name == "rag.access"]
    assert access_records
    record = access_records[-1]
    assert getattr(record, "kb_id", "-") == kb_id
