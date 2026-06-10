"""Orquestación del escaneo según configuración."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.core.config import Settings
from app.services.antivirus.clamav import scan_bytes_fake, scan_path_with_clamd
from app.services.antivirus.errors import MalwareDetectedError, ScannerUnavailableError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AntivirusScanOutcome:
    status: Literal["disabled", "skipped", "clean", "infected", "unavailable"]
    signature: str | None = None
    engine: str | None = None
    raw_response: str | None = None


def resolved_antivirus_backend(settings: Settings) -> Literal["fake", "clamd"]:
    if settings.environment == "test":
        return "fake"
    return "clamd"


def scan_upload_path(settings: Settings, path: Path) -> AntivirusScanOutcome:
    """Escanea un archivo en disco. Lanza si infectado o fail-closed sin daemon."""
    if not settings.clamav_enabled:
        return AntivirusScanOutcome(status="disabled")

    if not path.is_file():
        msg = "Archivo de upload no encontrado para antivirus."
        raise FileNotFoundError(msg)

    backend = resolved_antivirus_backend(settings)

    if backend == "fake":
        result = scan_bytes_fake(path, allow_eicar=settings.clamav_allow_eicar_test)
        engine = "fake"
    else:
        try:
            result = scan_path_with_clamd(
                path,
                host=settings.clamav_host,
                port=settings.clamav_port,
                timeout_seconds=settings.clamav_timeout_seconds,
            )
            engine = "clamd"
        except OSError as e:
            if settings.clamav_fail_open:
                logger.warning(
                    "ClamAV no disponible en %s:%s (%s); fail-open activo.",
                    settings.clamav_host,
                    settings.clamav_port,
                    e,
                )
                return AntivirusScanOutcome(status="skipped", engine="clamd")
            raise ScannerUnavailableError(str(e)) from e

    if result.clean:
        return AntivirusScanOutcome(
            status="clean",
            engine=engine,
            raw_response=result.raw_response,
        )

    signature = result.signature or "unknown"
    raise MalwareDetectedError(signature=signature, raw_response=result.raw_response)
