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
import subprocess

import httpx
import pytest

def _waf_base_url() -> str:
    explicit = os.environ.get("TEST_WAF_BASE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    legacy = os.environ.get("WAF_TEST_BASE_URL", "").strip()
    if legacy:
        return legacy.rstrip("/")
    if os.environ.get("TEST_WAF", "").strip() == "1":
        return "http://127.0.0.1"
    return ""


pytestmark = pytest.mark.skipif(
    not _waf_base_url(),
    reason="Define TEST_WAF_BASE_URL (p. ej. http://localhost) con el perfil waf activo.",
)

BASE = _waf_base_url() or "http://localhost"
WAF_MODE = os.environ.get("WAF_MODE", "DetectionOnly").strip()


@pytest.fixture
def client() -> httpx.Client:
    return httpx.Client(base_url=BASE, timeout=15.0)


def test_health_reaches_backend_through_waf(client: httpx.Client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body.get("status") in ("ok", "degraded")


def _waf_container_rule_engine() -> str | None:
    try:
        out = subprocess.run(
            [
                "docker",
                "inspect",
                "-f",
                "{{range .Config.Env}}{{println .}}{{end}}",
                "rag_waf",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    for line in out.stdout.splitlines():
        if line.startswith("MODSEC_RULE_ENGINE="):
            return line.split("=", 1)[1].strip()
    return None


def test_sqli_query_blocked_when_waf_mode_on(client: httpx.Client) -> None:
    if WAF_MODE != "On":
        pytest.skip("Solo aplica con WAF_MODE=On (bloqueo CRS).")
    engine = _waf_container_rule_engine()
    if engine != "On":
        pytest.skip(
            f"Contenedor rag_waf en MODSEC_RULE_ENGINE={engine!r}. "
            "Desde la raíz del repo: WAF_MODE=On ./scripts/recreate-waf.sh"
        )
    # Misma sonda que scripts/test-waf.sh (dispara CRS 942100 en logs)
    response = client.get("/api/health", params={"id": "1' OR 1=1--"})
    assert response.status_code == 403