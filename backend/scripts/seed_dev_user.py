"""Crea un usuario fijo para probar auth en Swagger (`/docs`).

Ejecutar desde la carpeta `backend/` (el paquete `app` debe importarse):

  cd backend && source .venv/bin/activate
  alembic upgrade head
  python -m scripts.seed_dev_user

Requiere Postgres accesible vía `DATABASE_URL` (p. ej. `docker compose up -d postgres`
en la raíz del repo y `127.0.0.1:5432` en el DSN).
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_engine
from app.models.user import User
from app.services.passwords import hash_password

# `example.com` es válido para documentación (RFC 2606). Dominios como `.test`
# los rechaza email-validator / EmailStr en Pydantic (uso reservado).
DEFAULT_EMAIL = "dev@example.com"
DEFAULT_PASSWORD = "RagLocalDev#2026"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", default=DEFAULT_EMAIL, help="Email único del usuario.")
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help="Contraseña en claro (solo para entornos locales).",
    )
    args = parser.parse_args()

    email = str(args.email).strip().lower()
    password = str(args.password)

    settings = get_settings()
    engine = get_engine()
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    try:
        with factory() as db:
            existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if existing is not None:
                print(f"Usuario ya existe (no se modifica): {email}", file=sys.stderr)
            else:
                db.add(
                    User(
                        email=email,
                        password_hash=hash_password(password, pepper=settings.password_pepper),
                        role="user",
                        is_active=True,
                    )
                )
                db.commit()
                print(f"Usuario creado: {email}")
    except Exception as e:
        err = str(e).lower()
        if "refused" in err or "could not connect" in err:
            print(
                "No se pudo conectar a Postgres. Levanta la base, por ejemplo:\n"
                "  cd .. && docker compose up -d postgres\n"
                "y usa en `backend/.env` un DATABASE_URL con host 127.0.0.1 y la misma "
                "contraseña que en docker-compose (usuario rag, DB rag).",
                file=sys.stderr,
            )
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()

    print()
    print("--- Swagger (/docs) — cuerpos de ejemplo ---")
    print()
    print("1) POST /api/auth/login")
    print('   { "email": "' + email + '", "password": "' + password + '" }')
    print()
    print("2) POST /api/auth/refresh  (pega refresh_token devuelto por login)")
    print('   { "refresh_token": "<refresh_token del login>" }')
    print()
    print("3) POST /api/auth/logout")
    print("   - Botón Authorize → HTTP Bearer → access_token del login")
    print("   - Cerrar sesión solo este refresh:")
    print(
        '   { "refresh_token": "<mismo refresh_token>", "all_devices": false }'
    )
    print("   - Cerrar en todos los dispositivos (refresh_token puede omitirse):")
    print('   { "refresh_token": null, "all_devices": true }')
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
