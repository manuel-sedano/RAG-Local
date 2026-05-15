"""Contexto en memoria entre etapas del pipeline de ingesta."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.chunking.engine import TextChunk
from app.services.parsing.types import ParsedDocument


@dataclass
class IngestPipelineContext:
    parsed: ParsedDocument | None = None
    normalized_text: str = ""
    artifact_paths: dict[str, Any] = field(default_factory=dict)
    chunks: list[TextChunk] = field(default_factory=list)
