# Backend (FastAPI en fases posteriores)

## Layout

- `app/api/` — rutas HTTP / WebSocket (`routes/` por dominio).
- `app/core/` — configuración y utilidades transversales.
- `app/db/` — SQLAlchemy, sesiones, repositorios.
- `app/services/` — lógica de negocio.
- `app/tasks/` — Celery / colas.
- `tests/` — pytest.

## Herramientas (ver `pyproject.toml`)

- **Lint:** Ruff (`ruff check app tests`)
- **Format:** Black + isort (`black app tests`, `isort app tests`)
- **Tests:** pytest (`pytest` desde esta carpeta)

### Instalación dev

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
ruff check app tests
black --check app tests
isort --check-only app tests
```
