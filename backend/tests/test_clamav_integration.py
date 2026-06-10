"""Integración opcional con clamd real (Docker perfil clamav).

Requiere:
  TEST_CLAMAV=1
  CLAMAV_HOST (default 127.0.0.1)
  CLAMAV_PORT (default 3310)
"""

from __future__ import annotations

import os
import socket
from pathlib import Path

import pytest

from app.core.config import clear_settings_cache, get_settings
from app.services.antivirus.clamav import EICAR_TEST_SIGNATURE, scan_path_with_clamd
from app.services.antivirus.scan import scan_upload_path


def _clamd_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.fixture
def clamav_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    if os.environ.get("TEST_CLAMAV", "").strip() != "1":
        pytest.skip("Define TEST_CLAMAV=1 y levanta `docker compose --profile clamav up -d`.")
    host = os.environ.get("CLAMAV_HOST", "127.0.0.1").strip()
    port = int(os.environ.get("CLAMAV_PORT", "3310"))
    if not _clamd_reachable(host, port):
        pytest.skip(f"clamd no accesible en {host}:{port}")

    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("CLAMAV_ENABLED", "true")
    monkeypatch.setenv("CLAMAV_HOST", host)
    monkeypatch.setenv("CLAMAV_PORT", str(port))
    monkeypatch.setenv("CLAMAV_FAIL_OPEN", "false")
    clear_settings_cache()


def test_clamd_detects_eicar(clamav_settings: None, tmp_path: Path) -> None:
    settings = get_settings()
    path = tmp_path / "eicar.com"
    path.write_bytes(EICAR_TEST_SIGNATURE)

    raw = scan_path_with_clamd(
        path,
        host=settings.clamav_host,
        port=settings.clamav_port,
        timeout_seconds=settings.clamav_timeout_seconds,
    )
    assert raw.clean is False
    assert raw.signature

    with pytest.raises(Exception) as exc:
        scan_upload_path(settings, path)
    assert "Malware" in type(exc.value).__name__ or "Eicar" in str(exc.value)
