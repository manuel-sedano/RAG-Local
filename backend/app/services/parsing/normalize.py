"""Limpieza y normalización de texto extraído."""

from __future__ import annotations

import re

from app.services.parsing.types import PageText, ParsedDocument

_MULTI_BLANK = re.compile(r"\n{3,}")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)", re.UNICODE)
_REPEATED_LINE = re.compile(r"(?m)^(.{4,80})\s*$\n(?:\1\s*$\n){2,}")


def normalize_whitespace(text: str) -> str:
    if not text:
        return ""
    out = text.replace("\r\n", "\n").replace("\r", "\n")
    out = _HYPHEN_BREAK.sub(r"\1\2", out)
    out = _MULTI_SPACE.sub(" ", out)
    out = _MULTI_BLANK.sub("\n\n", out)
    out = _REPEATED_LINE.sub(r"\1\n", out)
    return out.strip()


def normalize_parsed_document(parsed: ParsedDocument) -> ParsedDocument:
    pages: list[PageText] = []
    for page in parsed.pages:
        pages.append(
            PageText(
                page_number=page.page_number,
                text=normalize_whitespace(page.text),
                section=page.section,
            )
        )
    full_text = normalize_whitespace(parsed.full_text)
    if not full_text and pages:
        full_text = "\n\n".join(p.text for p in pages if p.text)
    return ParsedDocument(
        mime_type=parsed.mime_type,
        pages=pages,
        full_text=full_text,
        page_count=parsed.page_count,
        parser_used=parsed.parser_used,
        encoding=parsed.encoding,
        needs_ocr=parsed.needs_ocr,
        metadata=dict(parsed.metadata),
    )
