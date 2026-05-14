"""Handlers HTTP uniformes (modelo de error estándar)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.request_context import get_request_id


def _error_payload(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None,
    request_id: str | None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
        "request_id": request_id,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        rid = getattr(request.state, "request_id", None) or get_request_id()
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail:
            code = str(detail["code"])
            message = str(detail.get("message", code))
            details = detail.get("details")
            if not isinstance(details, dict):
                details = {}
        else:
            code = "HTTP_ERROR"
            message = str(detail) if detail else exc.__class__.__name__
            details = {}
        body = _error_payload(
            code=code,
            message=message,
            details=details,
            request_id=rid,
        )
        return JSONResponse(status_code=exc.status_code, content=body)
