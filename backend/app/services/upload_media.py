"""Validación de tipo MIME declarado y magic bytes (primeros bytes del archivo)."""

from __future__ import annotations


def magic_matches_declared_mime(*, declared_mime: str, head: bytes) -> bool:
    """Comprueba coherencia entre `Content-Type` y firma binaria mínima."""
    if declared_mime == "application/pdf":
        return head.startswith(b"%PDF")
    if declared_mime == ("application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
        return len(head) >= 4 and head[:4] == b"PK\x03\x04"
    if declared_mime == "text/plain":
        sample = head[:4096]
        if b"\x00" in sample:
            return False
        try:
            sample.decode("utf-8")
            return True
        except UnicodeDecodeError:
            try:
                sample.decode("latin-1")
                return True
            except UnicodeDecodeError:
                return False
    return False


def extension_for_mime(mime: str) -> str:
    if mime == "application/pdf":
        return ".pdf"
    if mime == ("application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
        return ".docx"
    if mime == "text/plain":
        return ".txt"
    return ""
