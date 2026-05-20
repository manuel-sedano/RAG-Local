"""Cliente mínimo INSTREAM para `clamd` (puerto 3310)."""

from __future__ import annotations

import logging
import socket
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

EICAR_TEST_SIGNATURE = (
    b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
)


@dataclass(frozen=True)
class ClamdScanResult:
    clean: bool
    signature: str | None
    raw_response: str


def _parse_clamd_response(raw: str, stream_name: str = "stream") -> ClamdScanResult:
    text = raw.strip()
    if not text:
        return ClamdScanResult(clean=True, signature=None, raw_response=text)

    line = text.splitlines()[-1].strip()
    if line.endswith(" OK"):
        return ClamdScanResult(clean=True, signature=None, raw_response=text)

    marker = " FOUND"
    if marker in line:
        # p. ej. "stream: Eicar-Signature FOUND"
        before_found = line.split(marker, 1)[0]
        if ":" in before_found:
            signature = before_found.split(":", 1)[1].strip()
        else:
            signature = before_found.strip()
        return ClamdScanResult(
            clean=False,
            signature=signature or "unknown",
            raw_response=text,
        )

    logger.warning("Respuesta ClamAV no reconocida (%s): %s", stream_name, text[:500])
    return ClamdScanResult(clean=True, signature=None, raw_response=text)


def scan_path_with_clamd(
    path: Path,
    *,
    host: str,
    port: int,
    timeout_seconds: float,
    chunk_size: int = 64 * 1024,
) -> ClamdScanResult:
    """Escanea un archivo con el protocolo zINSTREAM."""
    with socket.create_connection((host, port), timeout=timeout_seconds) as sock:
        sock.settimeout(timeout_seconds)
        sock.sendall(b"zINSTREAM\0")
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(chunk_size)
                if not chunk:
                    break
                sock.sendall(len(chunk).to_bytes(4, "big") + chunk)
        sock.sendall(b"\x00\x00\x00\x00")
        sock.shutdown(socket.SHUT_WR)

        chunks: list[bytes] = []
        while True:
            try:
                data = sock.recv(4096)
            except socket.timeout:
                break
            if not data:
                break
            chunks.append(data)

    raw = b"".join(chunks).decode("utf-8", errors="replace")
    return _parse_clamd_response(raw)


def scan_bytes_fake(path: Path, *, allow_eicar: bool) -> ClamdScanResult:
    """Detector local para tests (EICAR estándar)."""
    if not allow_eicar:
        return ClamdScanResult(clean=True, signature=None, raw_response="fake: skipped")

    head = path.read_bytes()[:65536]
    if EICAR_TEST_SIGNATURE in head:
        return ClamdScanResult(
            clean=False,
            signature="Eicar-Test-Signature",
            raw_response="fake: Eicar-Test-Signature FOUND",
        )
    return ClamdScanResult(clean=True, signature=None, raw_response="fake: OK")
