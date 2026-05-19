"""Cliente HTTP para Ollama (chat, reintentos, streaming)."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator
from typing import Any

import httpx

from app.core.config import Settings
from app.services.ollama.errors import OllamaError

logger = logging.getLogger(__name__)


def _chat_url(settings: Settings) -> str:
    return f"{settings.ollama_http_url.rstrip('/')}/api/chat"


def _should_retry(status: int | None, exc: Exception | None) -> bool:
    if exc is not None:
        return True
    if status is None:
        return False
    return status >= 500 or status == 429


def chat_completion(
    settings: Settings,
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float | None = None,
    stream: bool = False,
) -> dict[str, Any]:
    """POST /api/chat sin streaming; devuelve el JSON completo de Ollama."""
    if stream:
        msg = "Usa chat_completion_stream para stream=true."
        raise ValueError(msg)

    payload: dict[str, Any] = {
        "model": model or settings.llm_model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": settings.llm_temperature if temperature is None else temperature,
            "num_predict": settings.llm_max_tokens,
        },
    }

    timeout = httpx.Timeout(settings.ollama_timeout_seconds)
    last_exc: Exception | None = None
    attempts = settings.ollama_max_retries + 1

    for attempt in range(attempts):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(_chat_url(settings), json=payload)
                if response.status_code >= 400:
                    if _should_retry(response.status_code, None) and attempt < attempts - 1:
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    raise OllamaError(
                        f"Ollama respondió {response.status_code}: {response.text[:500]}"
                    )
                return response.json()
        except httpx.HTTPError as e:
            last_exc = e
            if attempt < attempts - 1:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise OllamaError(f"Error de red con Ollama: {e}") from e

    raise OllamaError(f"Ollama no respondió tras reintentos: {last_exc}")


def chat_completion_stream(
    settings: Settings,
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float | None = None,
) -> Iterator[str]:
    """POST /api/chat con stream=true; yield de fragmentos de texto (message.content)."""
    payload: dict[str, Any] = {
        "model": model or settings.llm_model,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": settings.llm_temperature if temperature is None else temperature,
            "num_predict": settings.llm_max_tokens,
        },
    }

    timeout = httpx.Timeout(settings.ollama_timeout_seconds)
    last_exc: Exception | None = None
    attempts = settings.ollama_max_retries + 1

    for attempt in range(attempts):
        try:
            with httpx.Client(timeout=timeout) as client:
                with client.stream("POST", _chat_url(settings), json=payload) as response:
                    if response.status_code >= 400:
                        body = response.read().decode("utf-8", errors="replace")
                        if _should_retry(response.status_code, None) and attempt < attempts - 1:
                            time.sleep(0.5 * (attempt + 1))
                            continue
                        raise OllamaError(
                            f"Ollama stream {response.status_code}: {body[:500]}"
                        )
                    for line in response.iter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        msg = data.get("message") or {}
                        piece = msg.get("content")
                        if piece:
                            yield str(piece)
                        if data.get("done"):
                            return
                    return
        except httpx.HTTPError as e:
            last_exc = e
            if attempt < attempts - 1:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise OllamaError(f"Error de red en stream Ollama: {e}") from e

    raise OllamaError(f"Stream Ollama falló tras reintentos: {last_exc}")


def extract_assistant_text(ollama_response: dict[str, Any]) -> str:
    msg = ollama_response.get("message") or {}
    content = msg.get("content")
    return (content or "").strip()


def extract_usage(ollama_response: dict[str, Any]) -> dict[str, int] | None:
    """Mapea eval_* de Ollama a prompt_tokens / completion_tokens aproximados."""
    prompt = ollama_response.get("prompt_eval_count")
    completion = ollama_response.get("eval_count")
    if prompt is None and completion is None:
        return None
    return {
        "prompt_tokens": int(prompt or 0),
        "completion_tokens": int(completion or 0),
    }
