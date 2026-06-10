"""Defensas contra prompt injection: consulta del usuario y chunks recuperados."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.config import Settings
from app.services.retrieval.types import SearchHit

# Patrones de inyección en texto de documentos (es/en).
_CHUNK_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "ignore_instructions",
        re.compile(
            r"(?i)(ignora|ignore|olvida|forget)\s+(todas?\s+)?(las\s+)?"
            r"(instrucciones|instructions|reglas|rules)"
        ),
    ),
    (
        "role_override",
        re.compile(r"(?i)(eres|you are|act as|actúa como)\s+(ahora|now)\s+"),
    ),
    (
        "system_prompt_leak",
        re.compile(r"(?i)(system\s+prompt|prompt del sistema|instrucciones del sistema)"),
    ),
    (
        "jailbreak",
        re.compile(r"(?i)(modo\s+)?(desarrollador|developer|DAN|jailbreak)"),
    ),
]

# Solicitudes de exfiltración / evasión en la pregunta del usuario.
_USER_BLOCK_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("exfil_system_prompt", re.compile(r"(?i)(mu[eé]strame|revela|dame|exporta|print)\s+.*(system\s+prompt|prompt del sistema)")),
    ("exfil_secrets", re.compile(r"(?i)(contraseñas?|passwords?|api[_\s-]?keys?|tokens?|secretos?)")),
    ("ignore_policy", re.compile(r"(?i)(ignora|olvida|bypass|elude|evade)\s+.*(seguridad|política|instrucciones|rules)")),
    ("impersonate_admin", re.compile(r"(?i)(actúa como|pretend to be|eres)\s+.*(admin|root|superusuario)")),
]

_STRIP_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)^\s*(system|assistant|user)\s*:\s*"),
    re.compile(r"(?i)```\s*(system|instrucciones?)\s*"),
    re.compile(r"(?is)<\s*script[^>]*>.*?</\s*script\s*>"),
]

_REFUSAL_ES = (
    "No puedo ayudar con esa solicitud porque intenta eludir las políticas de seguridad "
    "del asistente. Reformula tu pregunta sobre el contenido de los documentos de la base "
    "de conocimiento."
)


@dataclass
class UserQueryGuardResult:
    blocked: bool = False
    reasons: list[str] = field(default_factory=list)
    refusal_message: str | None = None


@dataclass
class ChunkGuardResult:
    safe_hits: list[SearchHit]
    ignored_chunk_ids: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def _match_patterns(text: str, patterns: list[tuple[str, re.Pattern[str]]]) -> list[str]:
    found: list[str] = []
    for name, rx in patterns:
        if rx.search(text):
            found.append(name)
    return found


def sanitize_chunk_text(text: str, *, max_chars: int | None = None) -> str:
    """Limpia texto de chunk antes de incluirlo en el prompt."""
    out = text.strip()
    for rx in _STRIP_PATTERNS:
        out = rx.sub("", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    if max_chars is not None and len(out) > max_chars:
        out = out[:max_chars] + "…"
    return out


def assess_user_query(content: str, settings: Settings) -> UserQueryGuardResult:
    """Bloquea consultas de exfiltración o evasión explícita."""
    if not settings.prompt_guard_enabled or not settings.prompt_guard_block_user_exfil:
        return UserQueryGuardResult(blocked=False)
    reasons = _match_patterns(content, _USER_BLOCK_PATTERNS)
    if not reasons:
        return UserQueryGuardResult(blocked=False)
    return UserQueryGuardResult(
        blocked=True,
        reasons=reasons,
        refusal_message=_REFUSAL_ES,
    )


def filter_search_hits(
    hits: list[SearchHit],
    settings: Settings,
) -> ChunkGuardResult:
    """Excluye chunks con señales fuertes de prompt injection."""
    if not settings.prompt_guard_enabled:
        return ChunkGuardResult(safe_hits=list(hits))

    safe: list[SearchHit] = []
    ignored: list[str] = []
    reasons: list[str] = []

    for hit in hits:
        raw = (hit.snippet or "").strip()
        chunk_reasons = _match_patterns(raw, _CHUNK_INJECTION_PATTERNS)
        if chunk_reasons:
            ignored.append(str(hit.chunk_id))
            reasons.extend(chunk_reasons)
            continue
        cleaned = sanitize_chunk_text(
            raw,
            max_chars=settings.prompt_guard_max_chunk_chars,
        )
        safe.append(
            SearchHit(
                chunk_id=hit.chunk_id,
                doc_id=hit.doc_id,
                score=hit.score,
                page=hit.page,
                snippet=cleaned,
                vector_score=hit.vector_score,
                bm25_score=hit.bm25_score,
                retrieval_score=hit.retrieval_score,
                rerank_score=hit.rerank_score,
            )
        )

    return ChunkGuardResult(
        safe_hits=safe,
        ignored_chunk_ids=ignored,
        reasons=sorted(set(reasons)),
    )


def build_safety_flags(
    *,
    user_guard: UserQueryGuardResult | None = None,
    chunk_guard: ChunkGuardResult | None = None,
) -> dict | None:
    """Payload JSON para `chat_messages.safety_flags`."""
    flags: dict = {}
    if user_guard and user_guard.blocked:
        flags["user_query_blocked"] = True
        flags["reasons"] = user_guard.reasons
        flags["user_notice"] = user_guard.refusal_message
    if chunk_guard and chunk_guard.ignored_chunk_ids:
        flags["ignored_chunks"] = len(chunk_guard.ignored_chunk_ids)
        flags["ignored_chunk_ids"] = chunk_guard.ignored_chunk_ids[:20]
        chunk_reasons = chunk_guard.reasons
        if chunk_reasons:
            flags.setdefault("reasons", [])
            if isinstance(flags["reasons"], list):
                flags["reasons"] = sorted(set(flags["reasons"] + chunk_reasons))
        flags["user_notice"] = (
            "Parte del contenido recuperado fue omitida por posibles instrucciones maliciosas incrustadas."
        )
    return flags or None
