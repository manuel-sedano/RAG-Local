"""Embeddings deterministas para tests (sin descargar modelos)."""

from __future__ import annotations

import hashlib
import math
import struct

from app.core.config import Settings


def _hash_to_unit_vector(text: str, dimension: int) -> list[float]:
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    counter = 0
    while len(values) < dimension:
        block = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        counter += 1
        for i in range(0, len(block) - 3, 4):
            raw = struct.unpack("!f", block[i : i + 4])[0]
            if math.isfinite(raw):
                values.append(raw)
            if len(values) >= dimension:
                break
    vec = values[:dimension]
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed_texts_fake(texts: list[str], settings: Settings) -> list[list[float]]:
    dim = settings.embedding_fake_dimension
    vectors = [_hash_to_unit_vector(t, dim) for t in texts]
    if settings.embedding_normalize:
        return vectors
    scale = 0.5
    return [[v * scale for v in vec] for vec in vectors]
