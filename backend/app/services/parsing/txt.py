"""Extracción de texto plano con detección de encoding."""

from __future__ import annotations

from pathlib import Path

from charset_normalizer import from_bytes

from app.services.parsing.errors import FatalParserError
from app.services.parsing.types import PageText, ParsedDocument


def _detect_and_decode(raw: bytes) -> tuple[str, str]:
    if not raw:
        return "", "utf-8"

    for encoding in ("utf-8", "utf-8-sig"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue

    # TXT legacy en español suele ser Latin-1; preferir antes que heurísticas amplias.
    try:
        return raw.decode("latin-1"), "latin-1"
    except UnicodeDecodeError:
        pass

    result = from_bytes(raw).best()
    if result is not None:
        return str(result), result.encoding or "unknown"

    raise FatalParserError(
        "txt_encoding_failed",
        "No se pudo decodificar el archivo de texto.",
    )


def extract_txt(path: Path) -> ParsedDocument:
    try:
        raw = path.read_bytes()
    except OSError as e:
        raise FatalParserError("txt_read_failed", f"No se pudo leer el TXT: {e}") from e

    text, encoding = _detect_and_decode(raw)
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    pages = [PageText(page_number=1, text=normalized.strip())] if normalized.strip() else []

    return ParsedDocument(
        mime_type="text/plain",
        pages=pages,
        full_text=normalized.strip(),
        page_count=1 if normalized.strip() else 0,
        parser_used="txt",
        encoding=encoding,
        needs_ocr=False,
        metadata={"byte_length": len(raw)},
    )
