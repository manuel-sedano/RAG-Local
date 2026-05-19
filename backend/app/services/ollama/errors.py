"""Errores del cliente Ollama."""

from __future__ import annotations


class OllamaError(RuntimeError):
    """Fallo al invocar la API de Ollama."""
