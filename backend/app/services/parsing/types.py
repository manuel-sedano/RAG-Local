"""Tipos compartidos del pipeline de parsing."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PageText:
    """Texto extraído de una página o bloque lógico (1-based)."""

    page_number: int
    text: str
    section: str | None = None


@dataclass(slots=True)
class ParsedDocument:
    """Resultado de extracción antes de normalización final."""

    mime_type: str
    pages: list[PageText]
    full_text: str
    page_count: int
    parser_used: str
    encoding: str | None = None
    needs_ocr: bool = False
    metadata: dict[str, object] = field(default_factory=dict)
