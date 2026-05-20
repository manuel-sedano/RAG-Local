"""Socket.IO: autenticación JWT (unitario)."""

from __future__ import annotations

import uuid

import pytest

from app.core.config import clear_settings_cache, get_settings
from app.realtime.auth import SocketAuthError, decode_socket_token
from app.services.jwt_tokens import create_access_token


@pytest.fixture(autouse=True)
def _env_test(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    clear_settings_cache()


def test_decode_socket_token_valid() -> None:
    settings = get_settings()
    token, _ = create_access_token(
        settings=settings,
        user_id=uuid.uuid4(),
        email="socket@test.com",
        role="user",
    )
    payload = decode_socket_token(token, settings)
    assert payload["type"] == "access"
    assert "sub" in payload


def test_decode_socket_token_invalid() -> None:
    settings = get_settings()
    with pytest.raises(SocketAuthError, match="inválido"):
        decode_socket_token("not-a-jwt", settings)
