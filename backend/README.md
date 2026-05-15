# Backend (FastAPI en fases posteriores)

## Layout

- `app/api/` — rutas HTTP / WebSocket (`routes/` por dominio).
- `app/core/` — configuración y utilidades transversales.
- `app/db/` — SQLAlchemy, sesiones, repositorios.
- `app/services/` — lógica de negocio.
- `app/tasks/` — Celery / colas.
- `tests/` — pytest.

## Herramientas (ver `pyproject.toml`)

Ejecuta **siempre** estos comandos **desde la carpeta `backend/`** (ahí existen `app/` y `tests/`). Si los lanzas desde la raíz del repo (`rag-local/`), Ruff fallará con `E902` al no encontrar esas rutas.

Con el venv activado, Black e isort están en el `PATH` del entorno; si no, usa `python -m black` y `python -m isort` para invocarlos desde el mismo Python que instaló `pip install -e ".[dev]"`.

- **Lint:** Ruff (`ruff check app tests`)
- **Format:** Black + isort (`python -m black app tests`, `python -m isort app tests`; o `black` / `isort` si el venv está activo)
- **Tests:** pytest (`pytest` desde esta carpeta). **Activa siempre** `source .venv/bin/activate` **antes** de `pytest`; si usas el Python del sistema sin dependencias instaladas, fallará con `ModuleNotFoundError` (p. ej. `pydantic`).

### Instalación dev

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
ruff check app tests
python -m black --check app tests
python -m isort --check-only app tests
```

### Tests de integración (`TEST_DATABASE_URL`)

Varios módulos (`test_auth_integration`, `test_kb_integration`, `test_documents_integration`, `test_migrations`) necesitan **Postgres real**. La variable **`TEST_DATABASE_URL`** debe apuntar a una base **solo para tests** (p. ej. `rag_test`), porque el código de prueba ejecuta **`DROP SCHEMA public CASCADE`** y vuelve a crear el esquema: **no uses la misma base que tu desarrollo (`rag`)**.

1. Levanta Postgres (desde la raíz del repo): `docker compose up -d postgres`
2. En WSL o terminal con acceso a `127.0.0.1:5432` (puerto publicado en `docker-compose.yml`):

   ```bash
   export TEST_DATABASE_URL="postgresql+psycopg://rag:rag_local_dev@127.0.0.1:5432/rag_test"
   ```

   Contraseña alineada con el servicio `postgres` del compose (`POSTGRES_PASSWORD`). Si creaste la base `rag_test` a mano, bien; si no, los tests suelen **crearla** al conectar a `postgres` como admin.

3. Ejecuta solo integración o toda la suite:

   ```bash
   cd backend
   source .venv/bin/activate
   pytest tests/test_documents_integration.py tests/test_kb_integration.py tests/test_auth_integration.py -v --tb=short
   pytest tests/ -q --tb=short
   ```

   **Importante:** ejecuta `pytest` **desde la carpeta `backend/`** (ahí está `pyproject.toml` y el paquete `app`). Si corres desde la raíz del repo, usa `pytest backend/tests/...` o `cd backend` primero.

   Redis opcional (rate limit con Redis real):

   ```bash
   docker compose up -d redis
   export TEST_REDIS_URL="redis://127.0.0.1:6379/15"
   cd backend && source .venv/bin/activate && pytest tests/test_auth_redis.py -v --tb=short
   ```

   Tras `pip install -e ".[dev]"`, instala también dependencias runtime del proyecto (p. ej. `python-multipart` para uploads); si falta alguna, `pip install -e .` de nuevo.

### Tests de parsing (`test_doc_parsers.py`)

No requieren Postgres. Solo el venv con dependencias instaladas (`pip install -e ".[dev]"` desde `backend/`):

```bash
cd backend
source .venv/bin/activate
pytest tests/test_doc_parsers.py -v --tb=short
```

Los tests de ingesta (`test_ingestion_worker.py`) sí necesitan `TEST_DATABASE_URL` y un PDF mínimo en `UPLOAD_STORAGE_DIR` (el fixture lo crea automáticamente).
