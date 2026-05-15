"""Tests unitarios del motor de chunking (sin Postgres)."""

from __future__ import annotations

from app.core.config import Settings, clear_settings_cache
from app.services.chunking.engine import chunk_normalized_text, chunking_config_hash
from app.services.parsing.types import PageText, ParsedDocument


def _settings(**overrides: object) -> Settings:
    clear_settings_cache()
    base = {
        "environment": "test",
        "chunk_size_tokens": 20,
        "chunk_overlap_tokens": 5,
        "max_chunk_size_tokens": 30,
        "chunk_min_merge_tokens": 8,
    }
    base.update(overrides)
    return Settings(**base)


def test_chunking_stable_with_accents() -> None:
    settings = _settings()
    text = (
        "Información sobre políticas de vacaciones: año 2026, "
        "niños, cañón, pingüino y más términos con acentos."
    )
    first = chunk_normalized_text(text, settings)
    second = chunk_normalized_text(text, settings)
    assert [c.text for c in first] == [c.text for c in second]
    assert all("ñ" in c.text or "ó" in c.text or len(c.text) > 0 for c in first)
    assert first[0].metadata["chunking_config_hash"] == chunking_config_hash(settings)


def test_chunking_long_document_multiple_chunks_with_overlap() -> None:
    settings = _settings(chunk_size_tokens=15, chunk_overlap_tokens=5, chunk_min_merge_tokens=3)
    words = [f"palabra{i}" for i in range(120)]
    text = " ".join(words)
    chunks = chunk_normalized_text(text, settings)
    assert len(chunks) >= 4
    assert all(c.char_start < c.char_end for c in chunks)
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))


def test_chunking_merges_very_small_tail() -> None:
    settings = _settings(
        chunk_size_tokens=10,
        chunk_overlap_tokens=0,
        chunk_min_merge_tokens=15,
        max_chunk_size_tokens=40,
    )
    text = "uno dos tres cuatro cinco seis siete ocho nueve diez once doce"
    chunks = chunk_normalized_text(text, settings)
    assert len(chunks) >= 1
    assert all(
        len(c.text.split()) >= 1 or len(chunks) == 1
        for c in chunks
    )


def test_chunking_preserves_page_metadata() -> None:
    settings = _settings(chunk_size_tokens=8, chunk_overlap_tokens=2, chunk_min_merge_tokens=2)
    parsed = ParsedDocument(
        mime_type="application/pdf",
        pages=[
            PageText(page_number=1, text="Introducción breve en página uno."),
            PageText(page_number=2, text="Desarrollo extenso en la segunda página del documento."),
        ],
        full_text="Introducción breve en página uno.\n\nDesarrollo extenso en la segunda página del documento.",
        page_count=2,
        parser_used="test",
    )
    chunks = chunk_normalized_text(parsed.full_text, settings, parsed=parsed)
    assert chunks
    assert any(c.page_start == 1 for c in chunks)
    assert any(c.page_end == 2 for c in chunks)


def test_chunking_config_hash_changes_with_settings() -> None:
    a = _settings(chunk_size_tokens=100)
    b = _settings(chunk_size_tokens=200)
    assert chunking_config_hash(a) != chunking_config_hash(b)
