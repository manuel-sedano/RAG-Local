"""Punto de entrada FastAPI: CORS, middlewares, logging y rutas."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.core.middleware import RequestIdMiddleware, SecurityHeadersMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    configure_logging(settings)
    logger.info(
        "Arranque del backend",
        extra={"environment": settings.environment},
    )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        lifespan=lifespan,
        title="rag-local-backend",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health_router, prefix="/api")

    @application.get("/")
    async def root() -> dict[str, str]:
        return {"service": "rag-local-backend", "api": "/api/health"}

    return application


app = create_app()
