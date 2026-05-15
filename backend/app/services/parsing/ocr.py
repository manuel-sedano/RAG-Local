"""OCR de PDF con Tesseract (páginas con poco texto o documento escaneado)."""

from __future__ import annotations

import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING

import fitz

from app.services.parsing.errors import RecoverableParserError
from app.services.parsing.normalize import normalize_whitespace
from app.services.parsing.types import PageText, ParsedDocument

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)

_PDF_MIME = "application/pdf"


def page_needs_ocr(page: PageText, min_chars_per_page: int) -> bool:
    return len(page.text.strip()) < min_chars_per_page


def document_needs_ocr(parsed: ParsedDocument, min_chars_per_page: int) -> bool:
    if parsed.mime_type != _PDF_MIME:
        return False
    if parsed.needs_ocr:
        return True
    return any(page_needs_ocr(p, min_chars_per_page) for p in parsed.pages)


def _ocr_cache_dir(upload_root: Path) -> Path:
    return upload_root / ".ocr_cache"


def _page_cache_key(pdf_path: Path, page_index: int, dpi: int) -> str:
    st = pdf_path.stat()
    digest = hashlib.sha256()
    digest.update(str(pdf_path.resolve()).encode())
    digest.update(f"{st.st_mtime_ns}:{st.st_size}:{page_index}:{dpi}".encode())
    return digest.hexdigest()


def _read_cache(cache_dir: Path, key: str) -> str | None:
    path = cache_dir / f"{key}.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return None


def _write_cache(cache_dir: Path, key: str, text: str) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{key}.txt").write_text(text, encoding="utf-8")


def _render_page_png(doc: fitz.Document, page_index: int, dpi: int) -> bytes:
    page = doc.load_page(page_index)
    pix = page.get_pixmap(dpi=dpi)
    return pix.tobytes("png")


def _tesseract_ocr_png(png_bytes: bytes, settings: Settings) -> str:
    import io

    try:
        import pytesseract
        from PIL import Image
    except ImportError as e:
        raise RecoverableParserError(
            "ocr_dependencies_missing",
            "Instala pytesseract y Pillow; en el sistema, tesseract-ocr y datos spa.",
        ) from e

    if settings.ocr_tesseract_cmd.strip():
        pytesseract.pytesseract.tesseract_cmd = settings.ocr_tesseract_cmd.strip()

    try:
        image = Image.open(io.BytesIO(png_bytes))
        text = pytesseract.image_to_string(image, lang=settings.ocr_tesseract_lang)
    except Exception as e:
        raise RecoverableParserError("ocr_tesseract_failed", f"Tesseract falló: {e}") from e

    return normalize_whitespace(text or "")


def _ocr_single_page(
    *,
    doc: fitz.Document,
    page_index: int,
    page_number: int,
    existing_text: str,
    settings: Settings,
    cache_dir: Path | None,
    pdf_path: Path,
) -> PageText:
    min_chars = settings.ocr_min_chars_per_page
    if len(existing_text.strip()) >= min_chars:
        return PageText(page_number=page_number, text=existing_text, ocr_applied=False)

    cache_key: str | None = None
    if cache_dir is not None and settings.ocr_cache_enabled:
        cache_key = _page_cache_key(pdf_path, page_index, settings.ocr_dpi)
        cached = _read_cache(cache_dir, cache_key)
        if cached is not None:
            merged = _merge_page_text(existing_text, cached)
            return PageText(page_number=page_number, text=merged, ocr_applied=True)

    png = _render_page_png(doc, page_index, settings.ocr_dpi)
    ocr_text = _tesseract_ocr_png(png, settings)

    if cache_key and cache_dir is not None and ocr_text:
        _write_cache(cache_dir, cache_key, ocr_text)

    merged = _merge_page_text(existing_text, ocr_text)
    return PageText(page_number=page_number, text=merged, ocr_applied=bool(ocr_text))


def _merge_page_text(native: str, ocr_text: str) -> str:
    native = native.strip()
    ocr_text = ocr_text.strip()
    if native and ocr_text:
        return f"{native}\n\n[OCR]\n{ocr_text}"
    return ocr_text or native


def _rebuild_full_text(pages: list[PageText]) -> str:
    return "\n\n".join(p.text for p in pages if p.text.strip())


def enrich_parsed_with_ocr(
    parsed: ParsedDocument,
    pdf_path: Path,
    settings: Settings,
    *,
    upload_root: Path | None = None,
) -> ParsedDocument:
    """Aplica OCR a páginas con poco texto y reconstruye el documento parseado."""
    if parsed.mime_type != _PDF_MIME:
        return parsed
    if not settings.ocr_enabled:
        return parsed
    if not document_needs_ocr(parsed, settings.ocr_min_chars_per_page):
        return parsed

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise RecoverableParserError(
            "pdf_open_failed",
            f"No se pudo abrir PDF para OCR: {e}",
        ) from e

    cache_dir = _ocr_cache_dir(upload_root) if upload_root and settings.ocr_cache_enabled else None
    pages_to_process: list[tuple[int, int, str]] = []
    for idx, page in enumerate(parsed.pages):
        if page_needs_ocr(page, settings.ocr_min_chars_per_page) or parsed.needs_ocr:
            pages_to_process.append((idx, page.page_number, page.text))

    if len(pages_to_process) > settings.ocr_max_pages:
        pages_to_process = pages_to_process[: settings.ocr_max_pages]
        logger.warning(
            "OCR limitado a %s páginas (ocr_max_pages).",
            settings.ocr_max_pages,
        )

    updated_pages = list(parsed.pages)
    ocr_count = 0

    def _process(item: tuple[int, int, str]) -> PageText:
        page_index, page_number, existing = item
        return _ocr_single_page(
            doc=doc,
            page_index=page_index,
            page_number=page_number,
            existing_text=existing,
            settings=settings,
            cache_dir=cache_dir,
            pdf_path=pdf_path,
        )

    workers = max(1, min(settings.ocr_max_workers, len(pages_to_process) or 1))
    if pages_to_process:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_process, item): item[0] for item in pages_to_process}
            for future in as_completed(futures):
                idx = futures[future]
                result = future.result()
                updated_pages[idx] = result
                if result.ocr_applied:
                    ocr_count += 1

    doc.close()

    full_text = _rebuild_full_text(updated_pages)
    if not full_text.strip():
        raise RecoverableParserError(
            "ocr_empty",
            "OCR no produjo texto legible en el documento.",
        )

    parser_used = parsed.parser_used
    if ocr_count > 0 and "tesseract" not in parser_used:
        parser_used = f"{parser_used}+tesseract"

    metadata = dict(parsed.metadata)
    metadata["ocr_pages_processed"] = ocr_count
    metadata["ocr_pages_capped"] = len(pages_to_process) >= settings.ocr_max_pages

    return ParsedDocument(
        mime_type=parsed.mime_type,
        pages=updated_pages,
        full_text=full_text,
        page_count=parsed.page_count,
        parser_used=parser_used,
        encoding=parsed.encoding,
        needs_ocr=False,
        metadata=metadata,
    )
