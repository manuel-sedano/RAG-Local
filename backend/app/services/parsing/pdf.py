"""Extracción de texto desde PDF con PyMuPDF."""

from __future__ import annotations

from pathlib import Path

import fitz

from app.services.parsing.errors import FatalParserError, RecoverableParserError
from app.services.parsing.types import PageText, ParsedDocument


def extract_pdf(
    path: Path,
    *,
    ocr_min_chars_per_page: int,
) -> ParsedDocument:
    try:
        doc = fitz.open(path)
    except Exception as e:
        raise FatalParserError("pdf_open_failed", f"No se pudo abrir el PDF: {e}") from e

    try:
        pages: list[PageText] = []
        total_chars = 0
        for idx in range(doc.page_count):
            page = doc.load_page(idx)
            text = (page.get_text("text") or "").strip()
            pages.append(PageText(page_number=idx + 1, text=text))
            total_chars += len(text)

        page_count = doc.page_count or max(len(pages), 1)
        avg_chars = total_chars / page_count if page_count else 0
        needs_ocr = page_count > 0 and avg_chars < ocr_min_chars_per_page

        full_text = "\n\n".join(p.text for p in pages if p.text)
        return ParsedDocument(
            mime_type="application/pdf",
            pages=pages,
            full_text=full_text,
            page_count=page_count,
            parser_used="pymupdf",
            needs_ocr=needs_ocr,
            metadata={
                "avg_chars_per_page": round(avg_chars, 2),
                "total_chars": total_chars,
            },
        )
    except RecoverableParserError:
        raise
    except FatalParserError:
        raise
    except Exception as e:
        raise RecoverableParserError(
            "pdf_extract_failed",
            f"Error al extraer texto del PDF: {e}",
        ) from e
    finally:
        doc.close()
