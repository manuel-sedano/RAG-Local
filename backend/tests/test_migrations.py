"""Pruebas de migración Alembic contra Postgres (opcional)."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine.url import make_url

from app.core.config import clear_settings_cache

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _ensure_database_exists(url: str) -> None:
    """Crea la base indicada en el DSN si no existe (conexión a `postgres`)."""
    u = make_url(url)
    dbname = u.database or ""
    if not dbname or dbname in ("postgres", "template0", "template1"):
        return
    if not re.fullmatch(r"[A-Za-z0-9_]+", dbname):
        msg = f"TEST_DATABASE_URL: nombre de base no seguro para DDL: {dbname!r}"
        raise ValueError(msg)
    admin = u.set(database="postgres")
    engine = create_engine(admin, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": dbname},
        ).first()
        if exists is None:
            conn.execute(text(f'CREATE DATABASE "{dbname}"'))
    engine.dispose()


@pytest.fixture(scope="session")
def postgres_migration_url() -> str:
    """Base dedicada recomendada (p. ej. `rag_test`); el test rehace `public`."""
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip(
            "Define TEST_DATABASE_URL (Postgres de test) para pruebas de migración."
        )
    _ensure_database_exists(url)
    return url


def _reset_public_schema(url: str) -> None:
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    engine.dispose()


def _alembic_config(url: str) -> Config:
    os.environ["DATABASE_URL"] = url
    clear_settings_cache()
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_alembic_upgrade_and_downgrade(postgres_migration_url: str) -> None:
    _reset_public_schema(postgres_migration_url)
    cfg = _alembic_config(postgres_migration_url)

    command.upgrade(cfg, "head")

    engine = create_engine(postgres_migration_url)
    try:
        insp = inspect(engine)
        assert insp.has_table("users")
        assert insp.has_table("message_citations")
        with engine.connect() as conn:
            rev = conn.execute(text("select version_num from alembic_version")).scalar_one()
        assert rev == "f7a2c9e01b34"
    finally:
        engine.dispose()

    command.downgrade(cfg, "base")

    engine = create_engine(postgres_migration_url)
    try:
        insp = inspect(engine)
        assert not insp.has_table("users")
    finally:
        engine.dispose()


def test_alembic_upgrade_idempotent(postgres_migration_url: str) -> None:
    _reset_public_schema(postgres_migration_url)
    cfg = _alembic_config(postgres_migration_url)
    command.upgrade(cfg, "head")
    command.upgrade(cfg, "head")

    engine = create_engine(postgres_migration_url)
    try:
        with engine.connect() as conn:
            n = conn.execute(text("select count(*) from alembic_version")).scalar_one()
        assert n == 1
    finally:
        engine.dispose()
