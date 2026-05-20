"""Detección de saludos conversacionales y fake LLM sin volcar CV."""

from __future__ import annotations

import uuid

import pytest

from app.core.config import get_settings
from app.services.chat.intent import is_conversational_message
from app.services.ollama.fake import fake_chat_completion
from app.services.retrieval.types import SearchHit


@pytest.mark.parametrize(
    "query",
    ["Saludos", "Hola", "Buenos días", "¡Hola!", "gracias"],
)
def test_is_conversational_greetings(query: str) -> None:
    assert is_conversational_message(query) is True


@pytest.mark.parametrize(
    "query",
    ["¿Cuál es su experiencia en Python?", "experiencia en Python", ""],
)
def test_is_conversational_not_greetings(query: str) -> None:
    assert is_conversational_message(query) is False


def test_fake_chat_saludos_with_hits_returns_greeting_not_cv_dump() -> None:
    settings = get_settings()
    hits = [
        SearchHit(
            chunk_id=uuid.uuid4(),
            doc_id=uuid.uuid4(),
            score=0.9,
            page=1,
            snippet="Experiencia en Python y Django durante 10 años en empresa X.",
        )
    ]
    text, _ = fake_chat_completion(settings, user_query="Saludos", hits=hits)
    assert "Resumen según" not in text
    assert "asistente" in text.lower() or "hola" in text.lower()
