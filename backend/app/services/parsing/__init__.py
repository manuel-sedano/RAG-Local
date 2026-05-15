"""Extracción y normalización de texto desde PDF, DOCX y TXT."""

from app.services.parsing.errors import FatalParserError, ParserError, RecoverableParserError
from app.services.parsing.orchestrator import parse_document_file
from app.services.parsing.types import PageText, ParsedDocument

__all__ = [
    "FatalParserError",
    "PageText",
    "ParsedDocument",
    "ParserError",
    "RecoverableParserError",
    "parse_document_file",
]
