"""Comprueba que el layout `app/` documentado en README exista."""

from __future__ import annotations

from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = BACKEND_ROOT / "app"


def test_expected_subpackages_exist() -> None:
    for name in ("api", "core", "db", "models", "services", "tasks"):
        pkg = APP_ROOT / name
        assert pkg.is_dir(), f"missing directory: {pkg.relative_to(BACKEND_ROOT)}"
        init_py = pkg / "__init__.py"
        assert init_py.is_file(), f"missing package marker: {init_py.relative_to(BACKEND_ROOT)}"
