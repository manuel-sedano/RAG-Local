"""Errores del pipeline de parsing."""


class ParserError(Exception):
    """Base para fallos de extracción de texto."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class RecoverableParserError(ParserError):
    """Fallo transitorio o recuperable (reintento o fallback)."""


class FatalParserError(ParserError):
    """Fallo definitivo del documento (formato corrupto, tipo no soportado)."""
