# Ejemplo de variables de entorno (`.env`)

Este archivo muestra un **ejemplo** de variables para ejecutar la plataforma local. Debe copiarse a la raíz del repo como `.env`.

> Importante: los comentarios y explicación están en español. No subas `.env` al repositorio.

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

# Tamaño máximo de upload (MB)
MAX_UPLOAD_MB=50

# Tipos permitidos (lista separada por coma)
ALLOWED_MIME_TYPES=application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain
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

# Parámetros retrieval (defaults)
RAG_VECTOR_TOP_K=50
RAG_BM25_TOP_K=50
RAG_RERANK_TOP_K=10
RAG_HYBRID_ENABLED=true
```

---

## Embeddings (Sentence Transformers)

```bash
# Modelo embeddings
EMBEDDING_MODEL_NAME=BAAI/bge-m3

# Batch size; ajustar según RAM
EMBEDDING_BATCH_SIZE=32

# Normalizar embeddings (recomendado para cosine)
EMBEDDING_NORMALIZE=true
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
```

---

## Seguridad: ClamAV / WAF / Proxy

```bash
# ClamAV
CLAMAV_ENABLED=true
CLAMAV_HOST=clamav
CLAMAV_PORT=3310

# WAF (si se usa contenedor separado)
WAF_ENABLED=true
WAF_MODE=DetectionOnly

# Traefik (rutas/hosts locales)
TRAEFIK_DASHBOARD_ENABLED=false
```

---

## Observabilidad (Prometheus/Grafana/Loki)

```bash
OBSERVABILITY_ENABLED=true

PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
LOKI_ENABLED=true

# Credenciales Grafana (cámbialas)
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin_local_change_me
```

---

## Notas y recomendaciones

- **Secrets**: genera `JWT_SECRET` y `PASSWORD_PEPPER` con un generador seguro.
- **CORS**: si cambias host/puerto del frontend, actualiza `CORS_ALLOW_ORIGINS`.
- **Uploads**: sube el límite `MAX_UPLOAD_MB` solo si tu máquina lo soporta; OCR+PDF grandes consumen RAM.
- **WAF**: inicia con `DetectionOnly` para observar falsos positivos, luego cambia a bloqueo.

