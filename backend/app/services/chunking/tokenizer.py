"""Conteo y segmentación aproximada de tokens (estable con UTF-8 y acentos)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_TOKEN_RE = re.compile(r"\S+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class TokenSpan:
    """Token con offsets de carácter en el texto original."""

    text: str
    char_start: int
    char_end: int


def count_tokens(text: str) -> int:
    """Cuenta tokens como secuencias de no-espacios (aprox. palabras)."""
    if not text:
        return 0
    return len(_TOKEN_RE.findall(text))


def tokenize_with_spans(text: str) -> list[TokenSpan]:
    """Tokeniza conservando posiciones de carácter (1-based indexing no aplica)."""
    return [
        TokenSpan(match.group(0), match.start(), match.end())
        for match in _TOKEN_RE.finditer(text)
    ]
