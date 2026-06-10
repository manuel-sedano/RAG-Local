# Ejemplo de variables de entorno (`.env`)

Plantilla de variables para ejecución local. Archivos versionados:

| Archivo | Uso |
|---------|-----|
| `.env.example` | Raíz: stack completo (Docker + backend). |
| `.env.test.example` / `.env.production.example` | Raíz: plantillas test / prod. |
| `backend/.env.example` | Overrides backend; ver también la `.env` de la raíz. |
| `frontend/.env.example` | Variables `NEXT_PUBLIC_*` para Next.js. |

**Arranque rápido:** `cp .env.example .env` en la raíz; opcional `cp backend/.env.example backend/.env` y `cp frontend/.env.example frontend/.env`.

Comentarios en español. El archivo `.env` queda fuera del control de versiones.

---

## Variables generales

```bash
# Entorno
ENVIRONMENT=local

# Hostnames/URLs externos (los que verá el navegador)
PUBLIC_BASE_URL=http://localhost
PUBLIC_API_BASE_URL=http://localhost/api

# CORS (separados por coma)
CORS_ALLOW_ORIGINS=http://localhost,http://127.0.0.1

# Logging
LOG_LEVEL=INFO
```

---

## Backend (FastAPI)

```bash
# Puerto interno del backend (normalmente detrás de Traefik)
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# Claves JWT (usa valores largos y aleatorios)
# Recomendación: mínimo 32-64 bytes (base64) o string largo.
JWT_ALG=HS256
JWT_ACCESS_TOKEN_EXPIRES_SECONDS=900
JWT_REFRESH_TOKEN_EXPIRES_SECONDS=2592000
JWT_SECRET=REEMPLAZAR_POR_UN_SECRETO_LARGO

# (Opcional) “Pepper” adicional para hashes sensibles
PASSWORD_PEPPER=REEMPLAZAR_POR_OTRO_SECRETO_LARGO

# Rate limiting en backend (por usuario/endpoint)
APP_RATE_LIMIT_ENABLED=true
APP_RATE_LIMIT_PER_MINUTE=120
INGEST_UPLOAD_MAX_PER_USER_PER_MINUTE=10
INGEST_UPLOAD_MAX_PER_KB_PER_MINUTE=20
RATE_LIMIT_AUDIT_ENABLED=true
AUTH_LOGIN_MAX_ATTEMPTS_PER_IP_PER_MINUTE=30
AUTH_LOGIN_MAX_ATTEMPTS_PER_EMAIL_PER_MINUTE=15

# Fail2ban (perfil Compose `fail2ban`; banaction dummy en WSL2)
FAIL2BAN_ENABLED=true
FAIL2BAN_PROFILE=fail2ban
FAIL2BAN_BANACTION=dummy
FAIL2BAN_SECURITY_LOG_ENABLED=true

# Tamaño máximo de upload (MB)
MAX_UPLOAD_MB=50

# Tipos permitidos (lista separada por coma)
ALLOWED_MIME_TYPES=application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain

# Parsing de documentos (ingesta)
PARSE_TIMEOUT_SECONDS=120
OCR_MIN_CHARS_PER_PAGE=40
PARSER_SAVE_ARTIFACTS=true
UNSTRUCTURED_ENABLED=false

# OCR (Tesseract en el host/contenedor; paquetes spa)
OCR_ENABLED=true
OCR_MAX_PAGES=50
OCR_TESSERACT_LANG=spa
OCR_CACHE_ENABLED=true
OCR_DPI=200
OCR_MAX_WORKERS=2
```

---

## PostgreSQL

```bash
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=rag
POSTGRES_USER=rag
POSTGRES_PASSWORD=rag_password_local

# URL completa para SQLAlchemy/Alembic (ejemplo)
DATABASE_URL=postgresql+psycopg://rag:rag_password_local@postgres:5432/rag
```

---

## Frontend (Next.js)

Expuesto al navegador solo variables `NEXT_PUBLIC_*`. Ejemplo en `frontend/.env.example`.

```bash
# Origen del backend (host:puerto). Sin barra final y sin sufijo /api (el cliente ya pide /api/...).
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Copia a `frontend/.env.local` y ajusta si el API corre en otro host/puerto. Si por error pones `.../api`, el front lo normaliza quitando `/api` para no duplicar rutas. El backend debe incluir el origen del front en `CORS_ALLOW_ORIGINS` (p. ej. `http://localhost:3000`).

---

## Redis / Celery

```bash
REDIS_HOST=redis
REDIS_PORT=6379

# Broker/result backend para Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Concurrencia del worker (ajustar según CPU/RAM)
CELERY_WORKER_CONCURRENCY=4
```

---

## Qdrant

```bash
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=rag_chunks_v1
QDRANT_ENABLED=true
QDRANT_UPSERT_BATCH_SIZE=64
QDRANT_SNIPPET_MAX_CHARS=500
QDRANT_TIMEOUT_SECONDS=30

# Tests opcionales contra Qdrant real (pytest, desde el host):
# TEST_QDRANT_URL=http://127.0.0.1:6333

# Parámetros retrieval (defaults)
RAG_VECTOR_TOP_K=50
RAG_BM25_TOP_K=50
RAG_RERANK_ENABLED=true
RAG_RERANK_CANDIDATE_TOP_K=30
RAG_RERANK_TOP_K=10
RAG_RERANK_BACKEND=auto
RAG_RERANK_MODEL_NAME=ms-marco-TinyBERT-L-2-v2
RAG_RERANK_MAX_LENGTH=256
RAG_RERANK_MAX_PASSAGE_CHARS=2000
RAG_RRF_K=60
RAG_SEARCH_MAX_TOP_K=50
RAG_HYBRID_ENABLED=true

# Producción/local con FlashRank real (pip install -e '.[rerank]'):
# RAG_RERANK_BACKEND=flashrank
```

---

## Embeddings (Sentence Transformers)

```bash
# Habilitar etapa embed en ingesta
EMBEDDING_ENABLED=true

# auto | fake | sentence_transformers (auto: fake en test, ST en local/prod)
EMBEDDING_BACKEND=auto

# Modelo embeddings (requiere pip install -e '.[embeddings]' en backend)
EMBEDDING_MODEL_NAME=BAAI/bge-m3

# Batch size; ajustar según RAM (OOM → reduce automático hasta EMBEDDING_BATCH_SIZE_MIN)
EMBEDDING_BATCH_SIZE=32
EMBEDDING_BATCH_SIZE_MIN=1

# Normalizar embeddings (recomendado para cosine)
EMBEDDING_NORMALIZE=true

# Timeout por batch de encode (segundos)
EMBEDDING_TIMEOUT_SECONDS=300
```

---

## Ollama (LLM local)

```bash
OLLAMA_HOST=ollama
OLLAMA_PORT=11434

# Nombre del modelo en Ollama (ajusta al tag real disponible)
LLM_MODEL=qwen2.5:7b-instruct

# Límites y comportamiento
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=800
LLM_STREAMING=true

# Instrucción global: forzar respuestas en español
LLM_FORCE_SPANISH=true
```

---

## Procesamiento de documentos

```bash
# Habilitar OCR (si false, solo OCR cuando se detecta PDF escaneado)
OCR_ENABLED=true

# Ruta a tesseract dentro del contenedor (si aplica)
TESSERACT_LANGS=spa

# Chunking
CHUNK_SIZE_TOKENS=500
CHUNK_OVERLAP_TOKENS=100
MAX_CHUNK_SIZE_TOKENS=800
CHUNK_MIN_MERGE_TOKENS=50
```

---

## Seguridad: ClamAV / WAF / Proxy

```bash
# ClamAV
CLAMAV_ENABLED=true
CLAMAV_HOST=clamav
CLAMAV_PORT=3310

# WAF (docker-compose.waf.yml + --profile waf)
WAF_ENABLED=true
WAF_MODE=DetectionOnly
WAF_MAX_BODY_BYTES=52428800
WAF_IMAGE=owasp/modsecurity-crs:4-nginx-alpine-202509220609

# Traefik (rutas/hosts locales)
TRAEFIK_DASHBOARD_ENABLED=false
```

---

## Observabilidad (Prometheus/Grafana/Loki)

```bash
OBSERVABILITY_ENABLED=true

PROMETHEUS_ENABLED=true
PROMETHEUS_METRICS_PATH=/metrics
PROMETHEUS_INCLUDE_KB_ID_LABEL=false
WORKER_PROMETHEUS_PORT=8001

GRAFANA_ENABLED=true
LOKI_ENABLED=true

# Credenciales Grafana (cámbialas; usadas por docker-compose en perfil observability)
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin_local_change_me
```

**Scrape (Docker):** Prometheus en el perfil `observability` apunta a `host.docker.internal:8000` (API) y `:8001` (worker). Arranca uvicorn y el worker Celery en el host antes del smoke (`bash scripts/test-observability.sh`).

---

## Tests backend (pytest / `TEST_DATABASE_URL`)

No va en el archivo `.env` de la app: se exporta **solo en la terminal** (o en `backend/.env.test` si lo cargas a mano).

- **Variable:** `TEST_DATABASE_URL` — DSN PostgreSQL **dedicado a tests** (p. ej. base `rag_test`).
- **Peligro:** varios tests hacen `DROP SCHEMA public CASCADE` en esa base; **no** uses la misma base que `rag` de desarrollo.
- **Ejemplo** (Postgres del `docker-compose.yml` expuesto en `127.0.0.1:5432`, usuario `rag`, password `rag_local_dev`):

  ```bash
  export TEST_DATABASE_URL="postgresql+psycopg://rag:rag_local_dev@127.0.0.1:5432/rag_test"
  cd backend && source .venv/bin/activate && pytest tests/ -q --tb=short
  ```

- **Redis opcional** (`tests/test_auth_redis.py`): `docker compose up -d redis`, luego `export TEST_REDIS_URL=redis://127.0.0.1:6379/15` y `cd backend && pytest tests/test_auth_redis.py -v` (el archivo vive bajo `backend/tests/`, no en la raíz del repo).

Detalle: `backend/.env.test.example` y `backend/README.md` (sección *Tests de integración*).

---

## Notas y recomendaciones

- **Secrets**: genera `JWT_SECRET` y `PASSWORD_PEPPER` con un generador seguro.
- **CORS**: si cambias host/puerto del frontend, actualiza `CORS_ALLOW_ORIGINS`.
- **Uploads**: sube el límite `MAX_UPLOAD_MB` solo si tu máquina lo soporta; OCR+PDF grandes consumen RAM.
- **WAF**: inicia con `DetectionOnly` para observar falsos positivos, luego cambia a bloqueo.

