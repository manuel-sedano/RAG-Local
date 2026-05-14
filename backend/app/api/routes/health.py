"""Endpoint de salud y dependencias."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.services.health_check import results_to_payload, run_dependency_checks

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> JSONResponse:
    settings = get_settings()
    results = await run_dependency_checks(settings)
    all_ok = all(r.ok for r in results)
    body = {
        "status": "ok" if all_ok else "degraded",
        "request_id": getattr(request.state, "request_id", None),
        "dependencies": results_to_payload(results),
    }
    if not all_ok:
        logger.warning(
            "Health degradado",
            extra={
                "dependencies": body["dependencies"],
                "request_id": body["request_id"],
            },
        )
    return JSONResponse(body, status_code=200 if all_ok else 503)
