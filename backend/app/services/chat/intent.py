"""Detección de mensajes conversacionales (sin RAG)."""

import re

_CONVERSATIONAL_RE = re.compile(
    r"^(?:\s*[¡¿]?\s*(?:hola|hello|hi|hey|saludos?|buenos\s+d[ií]as|buenas\s+tardes|"
    r"buenas\s+noches|qu[eé]\s+tal|buen\s+d[ií]a|buenas|"
    r"adi[oó]s|bye|gracias|thank\s+you|muchas\s+gracias)"
    r"[\s!?.¡,]*\s*)+$",
    re.IGNORECASE,
)

_FAREWELL_WORDS = ("adiós", "adios", "bye", "hasta luego", "nos vemos")


def is_conversational_message(query: str) -> bool:
    q = query.strip()
    if not q or len(q) > 80:
        return False
    return _CONVERSATIONAL_RE.match(q) is not None


def is_farewell_message(query: str) -> bool:
    q = query.strip().lower()
    return any(w in q for w in _FAREWELL_WORDS)
