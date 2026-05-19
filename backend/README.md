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

### Tests de chunking (`test_chunking.py`)

No requieren Postgres. Validan ventana deslizante, fusión de fragmentos pequeños, metadatos de página y hash de configuración:

```bash
cd backend
source .venv/bin/activate
pytest tests/test_chunking.py -v --tb=short
```

Variables opcionales (`.env` / export): `CHUNK_SIZE_TOKENS`, `CHUNK_OVERLAP_TOKENS`, `MAX_CHUNK_SIZE_TOKENS`, `CHUNK_MIN_MERGE_TOKENS`. Tras ingesta exitosa, revisa en Swagger o DB que `documents.chunk_count` y filas en `chunks` coincidan; en métricas del run: `chunk_count` y `chunking_config_hash`.

### Tests de embeddings (`test_embeddings.py`)

En `ENVIRONMENT=test` el backend de embeddings es **fake** (determinista, sin descargar modelos):

```bash
cd backend
source .venv/bin/activate
pytest tests/test_embeddings.py -v --tb=short
```

**Modelo real (local / Docker worker):**

```bash
pip install -e ".[embeddings]"
export EMBEDDING_BACKEND=sentence_transformers
# Primera ejecución descarga BAAI/bge-m3 (~2GB) en cache HuggingFace
```

Tras ingesta: `chunks.qdrant_point_id` = UUID del chunk; `chunks.embedding_model` = `bge-m3`; métricas `embedding_status`, `embedding_count`, `embedding_dim`.

**Tarea Celery dedicada (cola `embed`):** `app.tasks.embed.embed_document_chunks`

```bash
celery -A app.tasks.celery_app:celery_app worker -Q ingest,ocr,embed -l info
```

### Tests de OCR (`test_ocr.py`)

Usan **mocks** de Tesseract (no hace falta instalar el binario para pytest):

```bash
pytest tests/test_ocr.py -v --tb=short
```

**Prueba manual con Tesseract** (WSL/Ubuntu):

```bash
sudo apt-get install -y tesseract-ocr tesseract-ocr-spa
cd backend && source .venv/bin/activate && pip install -e ".[dev]"
# Sube un PDF escaneado por la UI o API; en métricas de ingesta: ocr_status=done
```

Worker Celery con cola OCR dedicada (cuando uses worker real, no solo eager):

```bash
celery -A app.tasks.celery_app:celery_app worker -Q ingest,ocr,embed -l info
```

### Tests de Qdrant (`test_qdrant_integration.py`)

Tras ingesta, los vectores se upsertan en la colección global **`rag_chunks_v1`** (cosine, dimensión del modelo de embeddings). Los tests de integración de ingesta desactivan Qdrant (`QDRANT_ENABLED=false`) para no depender del servicio.

**Qdrant real (opcional):**

```bash
docker compose up -d qdrant
export TEST_QDRANT_URL="http://127.0.0.1:6333"
cd backend && source .venv/bin/activate && pip install -e ".[dev]"
pytest tests/test_qdrant_integration.py -v --tb=short
```

Variables: `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_COLLECTION`, `QDRANT_ENABLED`, `QDRANT_SNIPPET_MAX_CHARS`. Al borrar un documento (soft delete), se eliminan puntos en Qdrant por filtro `kb_id` + `doc_id`. Payload documentado en `docs/10-database-schema.md`.

### Tests de retrieval híbrido

**Unitarios** (sin Postgres ni Qdrant):

```bash
cd backend && source .venv/bin/activate && pip install -e ".[dev]"
pytest tests/test_retrieval_unit.py -v --tb=short
```

**Integración HTTP** (`POST /api/kbs/{kb_id}/search`):

```bash
docker compose up -d postgres
export TEST_DATABASE_URL="postgresql+psycopg://rag:rag_local_dev@127.0.0.1:5432/rag_test"
pytest tests/test_retrieval_integration.py -v --tb=short
```

Opcional con Qdrant real (búsqueda vectorial en el mismo test):

```bash
docker compose up -d qdrant
export TEST_QDRANT_URL="http://127.0.0.1:6333"
pytest tests/test_retrieval_integration.py -v --tb=short
```

**Prueba manual (Swagger / curl):** tras login y con documentos en estado `READY`, ingesta habrá refrescado el índice BM25 en memoria del worker/API.

```bash
# Backend local (desde backend/, con .env y Postgres/Qdrant según docs/04-env-example.md)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Swagger: http://localhost:8000/docs → POST /api/kbs/{kb_id}/search
```

Variables: `RAG_HYBRID_ENABLED`, `RAG_VECTOR_TOP_K`, `RAG_BM25_TOP_K`, `RAG_RRF_K`, `RAG_SEARCH_MAX_TOP_K`, `RAG_RERANK_TOP_K` (reservado para FlashRank).
