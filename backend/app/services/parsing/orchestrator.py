"""Orquestación de extractores por MIME con timeout y fallback."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import TYPE_CHECKING

from app.services.parsing.docx import extract_docx
from app.services.parsing.errors import FatalParserError, ParserError, RecoverableParserError
from app.services.parsing.normalize import normalize_parsed_document
from app.services.parsing.pdf import extract_pdf
from app.services.parsing.txt import extract_txt
from app.services.parsing.types import ParsedDocument
from app.services.parsing.unstructured_fallback import try_unstructured_partition

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)

_PDF = "application/pdf"
_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_TXT = "text/plain"


def _extract_raw(path: Path, mime_type: str, settings: Settings) -> ParsedDocument:
    if mime_type == _PDF:
        return extract_pdf(path, ocr_min_chars_per_page=settings.ocr_min_chars_per_page)
    if mime_type == _DOCX:
        return extract_docx(path)
    if mime_type == _TXT:
        return extract_txt(path)
    raise FatalParserError("unsupported_mime", f"Tipo MIME no soportado para parsing: {mime_type}")


def _run_with_timeout(fn, timeout_seconds: float) -> ParsedDocument:
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn)
        try:
            return future.result(timeout=timeout_seconds)
        except FuturesTimeoutError as e:
            raise RecoverableParserError(
                "parse_timeout",
                f"La extracción superó el tiempo límite ({timeout_seconds}s).",
            ) from e


def parse_document_file(
    path: Path,
    mime_type: str,
    settings: Settings,
) -> ParsedDocument:
    """Extrae y normaliza texto de un archivo en disco."""
    if not path.is_file():
        raise FatalParserError("file_not_found", f"Archivo no encontrado: {path}")

    def _do_extract() -> ParsedDocument:
        try:
            parsed = _extract_raw(path, mime_type, settings)
        except RecoverableParserError:
            raise
        except FatalParserError:
            raise
        except ParserError:
            raise
        except Exception as e:
            raise RecoverableParserError("parse_failed", str(e)) from e

        if (
            settings.unstructured_enabled
            and (not parsed.full_text.strip() or parsed.needs_ocr)
            and mime_type in (_PDF, _DOCX)
        ):
            fallback = try_unstructured_partition(path, mime_type)
            if fallback and fallback.full_text.strip():
                logger.info("Parser primario insuficiente; se usó Unstructured para %s", path)
                parsed = fallback

        if not parsed.full_text.strip():
            raise FatalParserError(
                "empty_document",
                "El documento no contiene texto extraíble.",
            )

        return normalize_parsed_document(parsed)

    return _run_with_timeout(_do_extract, settings.parse_timeout_seconds)
