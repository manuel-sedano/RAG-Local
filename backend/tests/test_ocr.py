"""Tests de OCR Tesseract (mocks; no requiere binario tesseract en CI)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import fitz
import pytest

from app.core.config import Settings, clear_settings_cache
from app.services.parsing.ocr import (
    document_needs_ocr,
    enrich_parsed_with_ocr,
    page_needs_ocr,
)
from app.services.parsing.pdf import extract_pdf
from app.services.parsing.types import PageText, ParsedDocument


def _settings(**overrides) -> Settings:
    clear_settings_cache()
    return Settings(environment="test", **overrides)


def _write_scanned_pdf(path: Path, page_texts: list[str] | None = None) -> None:
    doc = fitz.open()
    for i in range(len(page_texts) if page_texts else 2):
        page = doc.new_page()
        if page_texts and page_texts[i]:
            page.insert_text((72, 72), page_texts[i])
    doc.save(path)
    doc.close()


def test_page_needs_ocr_threshold() -> None:
    assert page_needs_ocr(PageText(page_number=1, text=""), 40) is True
    assert page_needs_ocr(PageText(page_number=1, text="x" * 50), 40) is False


def test_document_needs_ocr_flag_or_pages() -> None:
    parsed = ParsedDocument(
        mime_type="application/pdf",
        pages=[PageText(page_number=1, text="")],
        full_text="",
        page_count=1,
        parser_used="pymupdf",
        needs_ocr=True,
    )
    assert document_needs_ocr(parsed, 40) is True

    parsed2 = ParsedDocument(
        mime_type="application/pdf",
        pages=[PageText(page_number=1, text="texto largo " * 10)],
        full_text="x",
        page_count=1,
        parser_used="pymupdf",
        needs_ocr=False,
    )
    assert document_needs_ocr(parsed2, 5) is False


@patch("app.services.parsing.ocr._tesseract_ocr_png")
def test_enrich_scanned_pdf_mock_tesseract(mock_ocr, tmp_path: Path) -> None:
    pdf_path = tmp_path / "scan.pdf"
    _write_scanned_pdf(pdf_path)
    parsed = extract_pdf(pdf_path, ocr_min_chars_per_page=40)
    assert parsed.needs_ocr is True

    mock_ocr.return_value = "Texto reconocido por OCR en español."

    settings = _settings(ocr_max_pages=10, ocr_cache_enabled=False)
    enriched = enrich_parsed_with_ocr(
        parsed,
        pdf_path,
        settings,
        upload_root=tmp_path / "uploads",
    )

    assert enriched.needs_ocr is False
    assert "Texto reconocido" in enriched.full_text
    assert enriched.metadata.get("ocr_pages_processed", 0) >= 1
    assert "tesseract" in enriched.parser_used
    mock_ocr.assert_called()


@patch("app.services.parsing.ocr._tesseract_ocr_png")
def test_mixed_pdf_only_low_text_pages_ocr(mock_ocr, tmp_path: Path) -> None:
    pdf_path = tmp_path / "mixed.pdf"
    _write_scanned_pdf(pdf_path, ["Página con mucho texto nativo extraído del PDF.", ""])

    parsed = extract_pdf(pdf_path, ocr_min_chars_per_page=40)
    mock_ocr.return_value = "Texto de la imagen escaneada."

    settings = _settings(ocr_min_chars_per_page=40, ocr_cache_enabled=False)
    enriched = enrich_parsed_with_ocr(parsed, pdf_path, settings, upload_root=tmp_path / "up")

    assert mock_ocr.call_count == 1
    assert "Texto de la imagen" in enriched.full_text
    assert "texto nativo" in enriched.full_text.lower() or "Página" in enriched.full_text


@patch("app.services.parsing.ocr._tesseract_ocr_png")
def test_ocr_cache_reuses_file(mock_ocr, tmp_path: Path) -> None:
    pdf_path = tmp_path / "cached.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(pdf_path)
    doc.close()
    parsed = extract_pdf(pdf_path, ocr_min_chars_per_page=40)
    mock_ocr.return_value = "Cacheado una vez."

    settings = _settings(ocr_cache_enabled=True)
    upload_root = tmp_path / "uploads"
    enrich_parsed_with_ocr(parsed, pdf_path, settings, upload_root=upload_root)
    assert mock_ocr.call_count == 1
    enrich_parsed_with_ocr(parsed, pdf_path, settings, upload_root=upload_root)
    assert mock_ocr.call_count == 1


@patch("app.services.parsing.ocr._tesseract_ocr_png")
def test_ocr_max_pages_cap(mock_ocr, tmp_path: Path) -> None:
    pdf_path = tmp_path / "many.pdf"
    doc = fitz.open()
    for _ in range(5):
        doc.new_page()
    doc.save(pdf_path)
    doc.close()

    parsed = ParsedDocument(
        mime_type="application/pdf",
        pages=[PageText(page_number=i + 1, text="") for i in range(5)],
        full_text="",
        page_count=5,
        parser_used="pymupdf",
        needs_ocr=True,
    )
    mock_ocr.return_value = "ok"

    settings = _settings(ocr_max_pages=2, ocr_cache_enabled=False)
    enriched = enrich_parsed_with_ocr(parsed, pdf_path, settings, upload_root=tmp_path / "u")

    assert mock_ocr.call_count <= 2
    assert enriched.metadata.get("ocr_pages_capped") is True


def test_celery_ocr_task_route(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    clear_settings_cache()
    from app.tasks.celery_app import create_celery_app

    app = create_celery_app()
    assert app.conf.task_routes["app.tasks.ocr.*"]["queue"] == "ocr"
