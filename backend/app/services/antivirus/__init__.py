"""Escaneo antivirus de uploads (ClamAV / fake en tests)."""

from app.services.antivirus.errors import MalwareDetectedError, ScannerUnavailableError
from app.services.antivirus.quarantine import quarantine_infected_document
from app.services.antivirus.scan import scan_upload_path

__all__ = [
    "MalwareDetectedError",
    "ScannerUnavailableError",
    "quarantine_infected_document",
    "scan_upload_path",
]
