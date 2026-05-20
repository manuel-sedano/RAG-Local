"""Errores del escaneo antivirus."""


class ScannerUnavailableError(Exception):
    """ClamAV no responde y fail-open está desactivado."""


class MalwareDetectedError(Exception):
    """Archivo infectado; el documento debe pasar a cuarentena."""

    def __init__(self, *, signature: str, raw_response: str) -> None:
        self.signature = signature
        self.raw_response = raw_response
        super().__init__(signature)
