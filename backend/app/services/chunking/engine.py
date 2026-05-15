"""Chunking por ventana deslizante con overlap, fusión de fragmentos y metadatos."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.document import Chunk, Document
from app.services.chunking.tokenizer import TokenSpan, count_tokens, tokenize_with_spans
from app.services.parsing.types import PageText, ParsedDocument

TOKENIZER_VERSION = "whitespace_v1"


@dataclass(frozen=True, slots=True)
class PageCharSpan:
    char_start: int
    char_end: int
    page_number: int
    section: str | None = None


@dataclass(frozen=True, slots=True)
class TextChunk:
    chunk_index: int
    text: str
    char_start: int
    char_end: int
    page_start: int | None
    page_end: int | None
    section: str | None
    metadata: dict[str, object] = field(default_factory=dict)


def chunking_config_hash(settings: Settings) -> str:
    payload = {
        "tokenizer_version": TOKENIZER_VERSION,
        "chunk_size_tokens": settings.chunk_size_tokens,
        "chunk_overlap_tokens": settings.chunk_overlap_tokens,
        "max_chunk_size_tokens": settings.max_chunk_size_tokens,
        "chunk_min_merge_tokens": settings.chunk_min_merge_tokens,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return digest[:16]


def _build_page_char_spans(pages: list[PageText]) -> list[PageCharSpan]:
    """Alinea offsets con el mismo criterio que `join` del pipeline (`\\n\\n`)."""
    spans: list[PageCharSpan] = []
    offset = 0
    non_empty = [p for p in pages if p.text.strip()]
    for idx, page in enumerate(non_empty):
        if idx > 0:
            offset += 2
        start = offset
        offset += len(page.text)
        spans.append(
            PageCharSpan(
                char_start=start,
                char_end=offset,
                page_number=page.page_number,
                section=page.section,
            )
        )
    return spans


def _pages_for_range(
    char_start: int,
    char_end: int,
    page_spans: list[PageCharSpan],
) -> tuple[int | None, int | None, str | None]:
    if not page_spans or char_end <= char_start:
        return None, None, None
    touched: list[PageCharSpan] = []
    for span in page_spans:
        if span.char_end <= char_start:
            continue
        if span.char_start >= char_end:
            break
        touched.append(span)
    if not touched:
        return None, None, None
    page_start = touched[0].page_number
    page_end = touched[-1].page_number
    section = next((s.section for s in touched if s.section), None)
    return page_start, page_end, section


def _sliding_window_chunks(
    tokens: list[TokenSpan],
    *,
    chunk_size: int,
    overlap: int,
    max_chunk: int,
) -> list[tuple[int, int]]:
    """Devuelve rangos (start_token_idx, end_token_idx) sobre la lista de tokens."""
    if not tokens:
        return []

    ranges: list[tuple[int, int]] = []
    start = 0
    n = len(tokens)
    step = max(1, chunk_size - overlap)

    while start < n:
        window = min(chunk_size, max_chunk)
        end = min(start + window, n)
        ranges.append((start, end))
        if end >= n:
            break
        start += step

    return ranges


def _merge_two_chunks(left: TextChunk, right: TextChunk, full_text: str) -> TextChunk:
    char_start = left.char_start
    char_end = right.char_end
    return TextChunk(
        chunk_index=0,
        text=full_text[char_start:char_end],
        char_start=char_start,
        char_end=char_end,
        page_start=_min_page(left.page_start, right.page_start),
        page_end=_max_page(left.page_end, right.page_end),
        section=left.section or right.section,
        metadata=dict(left.metadata),
    )


def _merge_small_chunks(
    chunks: list[TextChunk],
    full_text: str,
    *,
    min_tokens: int,
    max_chunk: int,
) -> list[TextChunk]:
    if len(chunks) <= 1:
        return chunks

    result = list(chunks)
    changed = True
    while changed:
        changed = False
        next_pass: list[TextChunk] = []
        i = 0
        while i < len(result):
            current = result[i]
            if count_tokens(current.text) < min_tokens and i + 1 < len(result):
                combined = _merge_two_chunks(current, result[i + 1], full_text)
                if count_tokens(combined.text) <= max_chunk:
                    next_pass.append(combined)
                    i += 2
                    changed = True
                    continue
            next_pass.append(current)
            i += 1
        result = next_pass

    return result


def _min_page(a: int | None, b: int | None) -> int | None:
    vals = [v for v in (a, b) if v is not None]
    return min(vals) if vals else None


def _max_page(a: int | None, b: int | None) -> int | None:
    vals = [v for v in (a, b) if v is not None]
    return max(vals) if vals else None


def chunk_normalized_text(
    text: str,
    settings: Settings,
    *,
    parsed: ParsedDocument | None = None,
) -> list[TextChunk]:
    """Divide texto normalizado en chunks con overlap y metadatos de página."""
    stripped = text.strip()
    if not stripped:
        return []

    page_spans = _build_page_char_spans(parsed.pages) if parsed and parsed.pages else []
    config_hash = chunking_config_hash(settings)

    tokens = tokenize_with_spans(stripped)
    token_ranges = _sliding_window_chunks(
        tokens,
        chunk_size=settings.chunk_size_tokens,
        overlap=settings.chunk_overlap_tokens,
        max_chunk=settings.max_chunk_size_tokens,
    )
    raw_chunks: list[TextChunk] = []
    for start_idx, end_idx in token_ranges:
        char_start = tokens[start_idx].char_start
        char_end = tokens[end_idx - 1].char_end
        chunk_text = stripped[char_start:char_end]
        page_start, page_end, section = _pages_for_range(char_start, char_end, page_spans)
        raw_chunks.append(
            TextChunk(
                chunk_index=len(raw_chunks),
                text=chunk_text,
                char_start=char_start,
                char_end=char_end,
                page_start=page_start,
                page_end=page_end,
                section=section,
                metadata={
                    "chunking_config_hash": config_hash,
                    "tokenizer_version": TOKENIZER_VERSION,
                    "token_count": count_tokens(chunk_text),
                },
            )
        )

    merged = _merge_small_chunks(
        raw_chunks,
        stripped,
        min_tokens=settings.chunk_min_merge_tokens,
        max_chunk=settings.max_chunk_size_tokens,
    )
    return [
        TextChunk(
            chunk_index=idx,
            text=c.text,
            char_start=c.char_start,
            char_end=c.char_end,
            page_start=c.page_start,
            page_end=c.page_end,
            section=c.section,
            metadata=dict(c.metadata),
        )
        for idx, c in enumerate(merged)
    ]


def persist_document_chunks(
    session: Session,
    document: Document,
    chunks: list[TextChunk],
    settings: Settings,
) -> int:
    """Reemplaza chunks del documento y actualiza chunk_count."""
    session.execute(delete(Chunk).where(Chunk.document_id == document.id))
    config_hash = chunking_config_hash(settings)
    embedding_model = settings.chunk_embedding_model_placeholder

    for chunk in chunks:
        meta = dict(chunk.metadata)
        meta.setdefault("chunking_config_hash", config_hash)
        session.add(
            Chunk(
                document_id=document.id,
                kb_id=document.kb_id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                section=chunk.section,
                chunk_metadata=meta,
                embedding_model=embedding_model,
                qdrant_point_id=None,
            )
        )

    document.chunk_count = len(chunks)
    session.add(document)
    session.flush()
    return len(chunks)
