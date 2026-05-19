"""LLM determinista para tests (sin Ollama)."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.services.retrieval.types import SearchHit

_NO_EVIDENCE_REPLY = (
    "No encontré evidencia suficiente en los documentos de esta base de conocimiento "
    "para responder con certeza. Te sugiero reformular la pregunta o subir material "
    "relacionado."
)


def fake_chat_completion(
    settings: Settings,
    *,
    user_query: str,
    hits: list[SearchHit],
    force_spanish: bool = True,
) -> tuple[str, dict[str, int]]:
    _ = (settings, force_spanish)
    if not hits:
        return _NO_EVIDENCE_REPLY, {"prompt_tokens": 0, "completion_tokens": len(_NO_EVIDENCE_REPLY)}

    sources = []
    for i, h in enumerate(hits[:5], start=1):
        page = f", pág. {h.page}" if h.page else ""
        sources.append(f"- Fragmento {i}{page} (chunk {h.chunk_id})")

    body = (
        f"Según los fragmentos recuperados, esto responde a tu consulta: «{user_query[:200]}».\n\n"
        "**Fuentes:**\n" + "\n".join(sources)
    )
    return body, {"prompt_tokens": 100, "completion_tokens": len(body) // 4}
