"""Cliente Ollama y backend fake para tests."""

from app.services.ollama.client import (
    chat_completion,
    chat_completion_stream,
    extract_assistant_text,
    extract_usage,
)
from app.services.ollama.errors import OllamaError
from app.services.ollama.fake import fake_chat_completion

__all__ = [
    "OllamaError",
    "chat_completion",
    "chat_completion_stream",
    "extract_assistant_text",
    "extract_usage",
    "fake_chat_completion",
]
