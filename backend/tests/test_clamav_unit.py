"""Tests unitarios de antivirus (fake / cuarentena en disco)."""

from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.core.config import clear_settings_cache, get_settings
from app.services.antivirus import MalwareDetectedError, quarantine_infected_document, scan_upload_path
from app.services.antivirus.clamav import EICAR_TEST_SIGNATURE, scan_bytes_fake
from app.services.document_service import QUARANTINED


def test_fake_scan_detects_eicar(tmp_path: Path) -> None:
    path = tmp_path / "eicar.txt"
    path.write_bytes(EICAR_TEST_SIGNATURE)
    result = scan_bytes_fake(path, allow_eicar=True)
    assert result.clean is False
    assert result.signature


def test_fake_scan_clean_file(tmp_path: Path) -> None:
    path = tmp_path / "ok.txt"
    path.write_text("hola mundo", encoding="utf-8")
    result = scan_bytes_fake(path, allow_eicar=True)
    assert result.clean is True


def test_scan_upload_path_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("CLAMAV_ENABLED", "false")
    clear_settings_cache()
    settings = get_settings()
    path = tmp_path / "a.txt"
    path.write_text("x", encoding="utf-8")
    outcome = scan_upload_path(settings, path)
    assert outcome.status == "disabled"


def test_scan_upload_path_raises_on_eicar(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("CLAMAV_ENABLED", "true")
    monkeypatch.setenv("CLAMAV_ALLOW_EICAR_TEST", "true")
    clear_settings_cache()
    settings = get_settings()
    path = tmp_path / "eicar.txt"
    path.write_bytes(EICAR_TEST_SIGNATURE)
    with pytest.raises(MalwareDetectedError) as exc:
        scan_upload_path(settings, path)
    assert "Eicar" in exc.value.signature


def test_quarantine_moves_file_and_logs_event(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("UPLOAD_STORAGE_DIR", str(upload_root))
    clear_settings_cache()
    settings = get_settings()

    kb_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    rel = f"{kb_id}/file.txt"
    src = upload_root / rel
    src.parent.mkdir(parents=True)
    src.write_bytes(EICAR_TEST_SIGNATURE)

    doc = SimpleNamespace(
        id=doc_id,
        kb_id=kb_id,
        uploaded_by_user_id=None,
        storage_path=rel,
        sha256="a" * 64,
        status="PROCESSING",
        error_code=None,
        error_message=None,
    )
    logged: list[dict] = []

    def _capture_log(db, **kwargs):  # noqa: ANN001
        logged.append(kwargs)

    monkeypatch.setattr(
        "app.services.antivirus.quarantine.log_security_event",
        _capture_log,
    )
    session = MagicMock()
    quarantine_infected_document(
        session,
        settings,
        doc,
        signature="Eicar-Test-Signature",
        raw_response="fake FOUND",
        engine="fake",
    )

    assert doc.status == QUARANTINED
    assert doc.error_code == "MALWARE_DETECTED"
    assert not src.is_file()
    assert (upload_root / f"quarantine/{kb_id}/{doc_id}.txt").is_file()
    assert doc.storage_path == f"quarantine/{kb_id}/{doc_id}.txt"
    assert len(logged) == 1
    assert logged[0]["kind"] == "DOCUMENT_QUARANTINED"
    assert logged[0]["details"]["signature"] == "Eicar-Test-Signature"
    session.add.assert_called()
