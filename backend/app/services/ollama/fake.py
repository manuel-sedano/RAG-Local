"""LLM determinista para tests (sin Ollama)."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.services.chat.intent import is_conversational_message, is_farewell_message
from app.services.retrieval.types import SearchHit

_NO_EVIDENCE_REPLY = (
    "No encontré evidencia suficiente en los documentos de esta base de conocimiento "
    "para responder con certeza. Te sugiero reformular la pregunta o subir material "
    "relacionado."
)

_GREETING_REPLY = (
    "¡Hola! Soy el asistente de esta base de conocimiento. "
    "Puedo ayudarte con preguntas sobre los documentos que hayas subido e indexado. "
    "¿En qué puedo ayudarte?"
)

_FAREWELL_REPLY = (
    "¡Hasta luego! Cuando quieras, vuelve a preguntar sobre tus documentos."
)


def fake_chat_completion(
    settings: Settings,
    *,
    user_query: str,
    hits: list[SearchHit],
    force_spanish: bool = True,
) -> tuple[str, dict[str, int]]:
    _ = (settings, force_spanish)
    if is_conversational_message(user_query):
        if is_farewell_message(user_query):
            text = _FAREWELL_REPLY
        else:
            text = _GREETING_REPLY
        return text, {"prompt_tokens": 0, "completion_tokens": len(text)}

    if not hits:
        return _NO_EVIDENCE_REPLY, {
            "prompt_tokens": 0,
            "completion_tokens": len(_NO_EVIDENCE_REPLY),
        }

    excerpts: list[str] = []
    sources: list[str] = []
    for i, h in enumerate(hits[:5], start=1):
        page = f", pág. {h.page}" if h.page else ""
        sources.append(f"- Fragmento {i}{page} (chunk {h.chunk_id})")
        snip = (h.snippet or "").strip()
        if snip:
            excerpts.append(f"**Fragmento {i}{page}:** {snip[:600]}")

    if excerpts:
        body = (
            f"Resumen según el material indexado para «{user_query[:200]}»:\n\n"
            + "\n\n".join(excerpts)
            + "\n\n**Fuentes:**\n"
            + "\n".join(sources)
        )
    else:
        body = (
            f"Encontré referencias en la base de conocimiento para «{user_query[:200]}», "
            "pero no pude leer el texto de los fragmentos.\n\n"
            "**Fuentes:**\n" + "\n".join(sources)
        )
    return body, {"prompt_tokens": 100, "completion_tokens": len(body) // 4}
