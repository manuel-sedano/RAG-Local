"""Fallback opcional con la librería Unstructured (si está instalada)."""

from __future__ import annotations

from pathlib import Path

from app.services.parsing.errors import RecoverableParserError
from app.services.parsing.types import PageText, ParsedDocument


def try_unstructured_partition(path: Path, mime_type: str) -> ParsedDocument | None:
    try:
        from unstructured.partition.auto import partition
    except ImportError:
        return None

    try:
        elements = partition(filename=str(path))
    except Exception as e:
        raise RecoverableParserError(
            "unstructured_failed",
            f"Unstructured no pudo particionar el archivo: {e}",
        ) from e

    texts: list[str] = []
    for el in elements:
        text = (getattr(el, "text", None) or str(el)).strip()
        if text:
            texts.append(text)

    if not texts:
        return None

    pages = [PageText(page_number=i + 1, text=t) for i, t in enumerate(texts)]
    full_text = "\n\n".join(texts)
    return ParsedDocument(
        mime_type=mime_type,
        pages=pages,
        full_text=full_text,
        page_count=len(pages),
        parser_used="unstructured",
        needs_ocr=False,
        metadata={"element_count": len(texts)},
    )
