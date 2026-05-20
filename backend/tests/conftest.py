"""Ajustes globales de pytest (entorno de test y caché de settings)."""

from __future__ import annotations

import os

import pytest

from app.core.config import clear_settings_cache

# Antes de importar `app.main` (que materializa settings y middlewares).
os.environ.setdefault("ENVIRONMENT", "test")

# WSL + Docker Desktop: 127.0.0.1 a veces no enruta; prueba gateway de /etc/resolv.conf.
if os.environ.get("TEST_DATABASE_URL", "").strip():
    from tests.postgres_url import ensure_test_database_url_env

    ensure_test_database_url_env()
if len(os.environ.get("JWT_SECRET", "")) < 16:
    os.environ["JWT_SECRET"] = "test_jwt_secret_" + "x" * 40

clear_settings_cache()


@pytest.fixture(autouse=True)
def _reset_settings_cache_after_test() -> None:
    yield
    clear_settings_cache()


def pytest_sessionfinish(session: object, exitstatus: object) -> None:
    """Nombres `session`/`exitstatus` son obligatorios (hookspec de pytest/pluggy)."""
    _ = (session, exitstatus)
    clear_settings_cache()
