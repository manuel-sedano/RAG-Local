"""Tests de fallback de retrieval para preguntas meta sobre documentos."""

from __future__ import annotations

import pytest

from app.services.retrieval.fallback import is_document_overview_query


@pytest.mark.parametrize(
    "query",
    [
        "de que va el PDF",
        "de qué va el PDF?",
        "¿De qué trata el documento?",
        "Resume el archivo",
        "resumen del pdf",
        "What is the document about?",
    ],
)
def test_is_document_overview_query_true(query: str) -> None:
    assert is_document_overview_query(query) is True


@pytest.mark.parametrize(
    "query",
    [
        "¿Cuál es la política de viáticos?",
        "experiencia en Python",
        "NOM-035",
        "Hola",
        "",
    ],
)
def test_is_document_overview_query_false(query: str) -> None:
    assert is_document_overview_query(query) is False
