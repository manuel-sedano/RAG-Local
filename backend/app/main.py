"""Punto de entrada FastAPI: CORS, middlewares, logging, Socket.IO y rutas."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from app.api.routes.auth import router as auth_router
from app.api.routes.chats import router as chats_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.api.routes.kbs import router as kbs_router
from app.api.routes.search import router as search_router
from app.core.config import get_settings
from app.core.error_handlers import register_error_handlers
from app.core.logging_config import configure_logging
from app.core.middleware import RequestIdMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit_middleware import UserRateLimitMiddleware
from app.db.session import get_engine
from app.realtime.server import create_socketio_server

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings)
    engine = get_engine()
    app.state.db_engine = engine
    app.state.db_session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    app.state.redis_client = None
    try:
        import redis as redis_mod

        r = redis_mod.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=0,
            decode_responses=True,
            socket_connect_timeout=2.0,
        )
        r.ping()
        app.state.redis_client = r
        logger.info("Redis disponible para rate limit de autenticación.")
    except Exception as e:
        logger.warning("Redis no disponible (rate limit de login desactivado): %s", e)
    logger.info(
        "Arranque del backend",
        extra={"environment": settings.environment},
    )
    yield
    redis_client = getattr(app.state, "redis_client", None)
    if redis_client is not None:
        redis_client.close()
    engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        lifespan=lifespan,
        title="rag-local-backend",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    register_error_handlers(application)

    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(UserRateLimitMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health_router, prefix="/api")
    application.include_router(auth_router, prefix="/api")
    application.include_router(kbs_router, prefix="/api")
    application.include_router(chats_router, prefix="/api")
    application.include_router(search_router, prefix="/api")
    application.include_router(documents_router, prefix="/api")

    @application.get("/")
    async def root() -> dict[str, str]:
        return {"service": "rag-local-backend", "api": "/api/health"}

    return application


app = create_app()


def build_asgi_application() -> socketio.ASGIApp | FastAPI:
    """App ASGI con Socket.IO montado (usar con uvicorn app.main:asgi_application)."""
    settings = get_settings()
    if not settings.socketio_enabled:
        return app
    sio = create_socketio_server(settings)
    app.state.sio = sio
    return socketio.ASGIApp(
        sio,
        app,
        socketio_path=settings.socketio_path,
    )


asgi_application = build_asgi_application()
