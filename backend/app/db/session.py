"""Motor síncrono y factoría de sesiones (Alembic y tests)."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def get_engine(*, url: str | None = None, **kwargs: object) -> Engine:
    """Crea un motor SQLAlchemy (por defecto desde settings)."""
    settings = get_settings()
    connect_url = url or settings.database_url
    return create_engine(connect_url, pool_pre_ping=True, **kwargs)  # type: ignore[arg-type]


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_session(url: str | None = None) -> Generator[Session, None, None]:
    """Dependencia FastAPI (futura): una sesión por request."""
    engine = get_engine(url=url)
    factory = get_session_factory(engine)
    session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
