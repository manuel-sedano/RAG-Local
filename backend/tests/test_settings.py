"""Validación de configuración (settings) por entorno."""

from __future__ import annotations

import pytest

from app.core.config import Settings, clear_settings_cache


def test_test_environment_allows_short_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("JWT_SECRET", "")
    clear_settings_cache()
    s = Settings()
    assert s.environment == "test"
    assert len(s.jwt_secret) >= 16


def test_local_requires_jwt_min_length(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("JWT_SECRET", "short")
    clear_settings_cache()
    with pytest.raises(ValueError):
        Settings()


def test_staging_requires_long_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("JWT_SECRET", "x" * 31)
    clear_settings_cache()
    with pytest.raises(ValueError):
        Settings()


def test_database_url_must_be_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp.db")
    clear_settings_cache()
    with pytest.raises(ValueError):
        Settings()
