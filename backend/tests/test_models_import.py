"""Los modelos ORM se importan y exponen tablas esperadas."""

from __future__ import annotations

import app.models as models


def test_user_tablename() -> None:
    assert models.User.__tablename__ == "users"


def test_chunk_metadata_column_name() -> None:
    assert "metadata" in models.Chunk.__table__.c
