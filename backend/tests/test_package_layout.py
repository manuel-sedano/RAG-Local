"""Smoke: el layout de paquetes importa sin FastAPI aún instalado."""


def test_app_package_importable() -> None:
    import app  # noqa: F401

    assert app.__doc__
