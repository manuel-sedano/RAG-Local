"""Tests opcionales contra el WAF real (Traefik -> ModSecurity CRS -> backend).

Requisitos:

  docker compose -f docker-compose.yml -f docker-compose.waf.yml --profile waf up -d
  export TEST_WAF_BASE_URL=http://localhost

Con bloqueo activo:

  export WAF_MODE=On
  docker compose -f docker-compose.yml -f docker-compose.waf.yml --profile waf up -d --force-recreate waf
"""

from __future__ import annotations

import os

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_WAF_BASE_URL", "").strip(),
    reason="Define TEST_WAF_BASE_URL (p. ej. http://localhost) con el perfil waf activo.",
)

BASE = os.environ.get("TEST_WAF_BASE_URL", "http://localhost").rstrip("/")
WAF_MODE = os.environ.get("WAF_MODE", "DetectionOnly").strip()


@pytest.fixture
def client() -> httpx.Client:
    return httpx.Client(base_url=BASE, timeout=15.0)


def test_health_reaches_backend_through_waf(client: httpx.Client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body.get("status") in ("ok", "degraded")


def test_sqli_query_blocked_when_waf_mode_on(client: httpx.Client) -> None:
    if WAF_MODE != "On":
        pytest.skip("Solo aplica con WAF_MODE=On (bloqueo CRS).")
    response = client.get("/api/health", params={"id": "1' OR '1'='1--"})
    assert response.status_code == 403