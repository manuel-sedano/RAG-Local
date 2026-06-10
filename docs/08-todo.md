# TODO maestro — por fases y feature branches

Este archivo es el backlog ejecutable del proyecto. Está organizado por:

- **Fases** (orden recomendado de entrega)
- **Features** (áreas funcionales)
- **Ramas Git** (feature branches sugeridas)

Reglas:

- **Cada tarea** usa checkbox Markdown.
- Las tareas están separadas por backend/frontend/docker/testing/docs/security/observability.
- Las ramas sugeridas se pueden dividir en PRs pequeños.

**Contexto:** el árbol objetivo incluye `frontend/`, `backend/`, `docker/`, `scripts/`, `uploads/` y `docker-compose.yml`. Las tareas siguientes cubren la implementación.

---

## Fase 0 — Bootstrap del repositorio y base operativa

### Feature branch: `chore/repo-bootstrap`

- [x] ~~Crear estructura de carpetas: `frontend/`, `backend/`, `docker/`, `scripts/`, `uploads/`~~ — Carpetas + `README`/`scripts` y `uploads/.gitkeep`.
- [x] ~~Crear `.gitignore` robusto (node_modules, .env, uploads, volúmenes, caches, modelos)~~ — Reglas para Python, Node, `.env`, `uploads/**`, modelos, caches, IDE.
- [x] ~~Definir convención de nombres para servicios/volúmenes/redes~~ — `docker/CONVENTIONS.md` (red `rag_net`, volúmenes `rag_vol_*`, perfiles `clamav` / `observability`).
- [x] ~~Crear `docker-compose.yml` base con servicios:~~ — `docker-compose.yml` en la raíz.
  - [x] ~~`traefik`~~ — `traefik:v3.2`, config en `docker/traefik/traefik.yml`, métricas Prometheus.
  - [x] ~~`frontend` (placeholder)~~ — build `docker/placeholders/frontend` (nginx + página estática, `/health`).
  - [x] ~~`backend` (placeholder)~~ — build `docker/placeholders/backend` (nginx, `/api/health` JSON).
  - [x] ~~`worker` (placeholder)~~ — Alpine `sleep infinity`, monta `rag_vol_uploads` en `/uploads`.
  - [x] ~~`postgres`~~ — `postgres:16-alpine`, volumen `rag_vol_postgres`, healthcheck.
  - [x] ~~`redis`~~ — `redis:7-alpine`, healthcheck.
  - [x] ~~`qdrant`~~ — `qdrant/qdrant:v1.12.4`, volumen `rag_vol_qdrant`.
  - [x] ~~`ollama`~~ — `ollama/ollama:latest`, volumen `rag_vol_ollama`.
  - [x] ~~`clamav` (opcional en MVP; recomendado temprano)~~ — perfil `clamav`, imagen oficial, volumen `rag_vol_clamav`.
  - [x] ~~`prometheus`, `grafana`, `loki` (opcional por fase)~~ — perfil `observability`; Traefik en `/prometheus` y `/grafana/`; Loki solo red interna.
- [x] ~~Definir redes:~~
  - [x] ~~una red interna (p. ej. `rag_net`)~~ — bridge `rag_net`.
  - [x] ~~exponer solo Traefik a host (80/443)~~ — únicos `ports:` en el servicio `traefik`.
- [x] ~~Definir volúmenes persistentes:~~
  - [x] ~~Postgres~~ — `rag_vol_postgres`
  - [x] ~~Qdrant~~ — `rag_vol_qdrant`
  - [x] ~~Ollama models~~ — `rag_vol_ollama`
  - [x] ~~uploads~~ — `rag_vol_uploads` (montado en `worker`)
- [x] ~~Documentar “smoke test” mínimo (health endpoints y verificación)~~ — `docs/02-smoke-test.md`

### Feature branch: `chore/dev-tooling`

- [x] ~~Backend:~~
  - [x] ~~elegir herramientas de lint/format (ruff/black/isort) y fijar config~~ — `backend/pyproject.toml` (Ruff, Black, isort).
  - [x] ~~agregar `pyproject.toml` con config de tooling~~ — mismo archivo + extras `dev` (pytest, pytest-asyncio).
  - [x] ~~definir estructura `backend/app/` (API, core, db, services, tasks)~~ — paquetes vacíos documentados.
  - [x] ~~configurar `pytest` y carpeta `backend/tests/`~~ — `tests/test_package_layout.py`, `pytest` en `pyproject`.
- [x] ~~Frontend:~~
  - [x] ~~inicializar Next.js (App Router o Pages; documentar decisión)~~ — Next 16 + **App Router** + `src/`; decisión en `frontend/README.md`.
  - [x] ~~configurar Tailwind~~ — Tailwind 3 + tema shadcn en `tailwind.config.ts` y `globals.css`.
  - [x] ~~integrar shadcn/ui~~ — `components.json`, `Button` en `src/components/ui/`, `cn` en `src/lib/utils.ts`.
  - [x] ~~configurar ESLint~~ — flat config consumiendo `eslint-config-next/core-web-vitals`; script `npm run lint`.
  - [x] ~~definir estructura `frontend/src/` (components, app, lib, hooks)~~ — `src/app`, `src/components`, `src/lib`, `src/hooks/`.
- [x] ~~Scripts:~~
  - [x] ~~agregar `scripts/` con comandos repetibles (backup, reindex, reset dev)~~ — `backup.sh`, `reindex.sh`, `reset-dev.sh` (stubs) + `scripts/README.md`.

### Feature branch: `docs/initial-docs-sync`

- [x] ~~Revisar y alinear `README.md` y `docs/*.md` con la estructura final del repo~~ — Árbol en README, desarrollo local vs Docker, índice `docs/README.md` y enlaces coherentes.
- [x] ~~Crear plantilla de PR (si se decide) y convención de issues (opcional)~~ — `.github/pull_request_template.md` + `docs/16-github-issues.md` + referencias en `03-github-workflow.md`.
- [x] ~~Definir estándares de respuesta del asistente (siempre en español) en un doc de producto (opcional)~~ — `docs/15-asistente-respuestas.md` enlazado desde README.

---

## Fase 1 — Fundaciones backend (DB, config, health, base API)

### Feature branch: `feat/backend-core`

- [x] ~~Configuración:~~
  - [x] ~~implementar loader de `.env` (pydantic settings)~~ — `app/core/config.py` + `pydantic-settings` (`env_file` `.env` / `../.env`).
  - [x] ~~separar settings por ambiente (`local`, `test`)~~ — `environment` + validación distinta en `test` vs `local`/`staging`/`production`.
  - [x] ~~validar settings al boot (fallar rápido)~~ — `Settings.validate_boot` (JWT, `DATABASE_URL`).
- [x] ~~Logging:~~
  - [x] ~~logging estructurado (JSON o key-value) con `request_id`~~ — `app/core/logging_config.py` (JSON) + `RequestIdFilter`.
  - [x] ~~middleware de `request_id` (propagar en logs/responses)~~ — `RequestIdMiddleware` + cabecera `X-Request-ID`.
  - [x] ~~sanitizar logs (no tokens, no passwords)~~ — `RedactAttributesFilter` + redacción en formatter (`password`, `token`, `secret`, …).
- [x] ~~Health:~~
  - [x] ~~endpoint `GET /api/health`~~ — `app/api/routes/health.py`.
  - [x] ~~chequeo de Postgres, Redis, Qdrant, Ollama~~ — `app/services/health_check.py`.
  - [x] ~~retornar `503` si dependencia crítica cae~~ — `503` si alguna dependencia falla.
- [x] ~~Seguridad base:~~
  - [x] ~~headers de seguridad (via Traefik y/o FastAPI)~~ — `SecurityHeadersMiddleware`.
  - [x] ~~CORS restringido por `CORS_ALLOW_ORIGINS`~~ — `CORSMiddleware` con orígenes desde settings.

### Feature branch: `feat/db-schema-alembic`

- [x] ~~DB:~~
  - [x] ~~definir modelos SQLAlchemy para tablas core:~~
    - [x] ~~`users`~~
    - [x] ~~`refresh_tokens`~~
    - [x] ~~`knowledge_bases`~~
    - [x] ~~`kb_memberships` (multiusuario)~~
    - [x] ~~`documents`~~
    - [x] ~~`document_ingestion_runs`~~
    - [x] ~~`chunks`~~
    - [x] ~~`chats`~~
    - [x] ~~`chat_messages`~~
    - [x] ~~`message_citations`~~
    - [x] ~~`security_events` (opcional)~~
    - [x] ~~`rate_limit_events` (opcional)~~
  - [x] ~~crear migraciones Alembic iniciales~~
  - [x] ~~crear índices recomendados (GIN/BTREE)~~
- [x] ~~Testing:~~
  - [x] ~~fixture de DB test (Postgres en Docker o sqlite compatible si viable)~~
  - [x] ~~test de migración (alembic upgrade head)~~

---

## Fase 2 — Autenticación y autorización

## Feature: auth (JWT)

### Feature branch: `feat/auth-jwt`

- [x] ~~Backend:~~
  - [x] ~~modelo `User` + validaciones (email único, is_active)~~ — modelo en esquema; login con `EmailStr` + email normalizado a minúsculas.
  - [x] ~~hashing de passwords (Argon2id o bcrypt con costo alto)~~ — Argon2id + `PASSWORD_PEPPER` (`app/services/passwords.py`).
  - [x] ~~servicio JWT:~~
    - [x] ~~emitir access token con TTL corto~~ — `jwt_access_token_expires_seconds` (default 900s).
    - [x] ~~emitir refresh token con TTL largo~~ — token opaco + fila `refresh_tokens` con `jwt_refresh_token_expires_seconds`.
    - [x] ~~incluir `jti` en access~~ — `app/services/jwt_tokens.py`.
  - [x] ~~refresh token store:~~
    - [x] ~~persistir hash de refresh en DB~~ — SHA-256 del token opaco en `token_hash`.
    - [x] ~~rotación de refresh (invalidate old, create new)~~ — `rotate_refresh_token` en `auth_service.py`.
    - [x] ~~revocación por logout~~ — `revoked_at` + `all_devices` revoca todas las filas activas.
  - [x] ~~endpoints:~~
    - [x] ~~`POST /api/auth/login`~~ — `app/api/routes/auth.py`
    - [x] ~~`POST /api/auth/refresh`~~
    - [x] ~~`POST /api/auth/logout`~~
  - [x] ~~dependencias FastAPI:~~
    - [x] ~~`get_current_user` (bearer)~~
    - [x] ~~`require_role` / `require_kb_access`~~ — `require_app_roles(...)` y `require_kb_access` / `ensure_kb_access` en `app/api/deps.py`.
  - [x] ~~rate limit:~~
    - [x] ~~login rate limit por IP + email~~ — Redis + `check_login_rate_limits` (si Redis no conecta, se omite).
    - [x] ~~lockout progresivo por usuario~~ — `record_failed_password_attempt` + TTL exponencial acotado.
  - [x] ~~auditoría:~~
    - [x] ~~registrar `LOGIN_FAILED`, `LOGIN_SUCCESS`, `TOKEN_REFRESH`, `LOGOUT`~~ — `security_events` vía `auth_audit.py` / `auth_service.py`.
- [x] ~~Frontend:~~
  - [x] ~~UI login (shadcn/ui)~~ — `src/app/login/` + Input/Label/Card.
  - [x] ~~estado de sesión (access/refresh)~~ — `localStorage` + `AuthProvider` / `useAuth`.
  - [x] ~~interceptor Axios para `401` → refresh → retry~~ — `src/lib/api-client.ts`.
  - [x] ~~logout~~ — botón inicio + `POST /api/auth/logout` con `all_devices` si no hay refresh.
  - [x] ~~manejo de expiración y mensajes al usuario en español~~ — aviso en login con `?expired=1`; errores de API en español donde aplica.
- [ ] Testing:
  - [x] ~~unit tests hashing/JWT~~ — `tests/test_auth_crypto.py` (rate limit con Redis fake en memoria en el propio test).
  - [x] ~~integration tests login/refresh/logout~~ — `tests/test_auth_integration.py` (requiere `TEST_DATABASE_URL`).
  - [x] ~~tests de lockout/rate limit con **Redis real** (opcional; hoy fake en memoria en tests unitarios)~~ — `tests/test_auth_redis.py` con `TEST_REDIS_URL` (p. ej. `redis://127.0.0.1:6379/15`).
- [x] ~~Docs:~~
  - [x] ~~confirmar que `docs/09-api-spec.md` coincide con implementación real~~ — refresh opaco documentado; contrato login/refresh/logout alineado.

---

## Fase 3 — Knowledge Bases (KB)

## Feature: knowledge bases

### Feature branch: `feat/kb-crud`

- [x] ~~Backend:~~
  - [x] ~~modelo `KnowledgeBase`~~ — ya en esquema Alembic; CRUD en `kbs.py` + `kb_service.py`.
  - [x] ~~(si multiusuario) modelo `kb_memberships` y roles por KB~~ — modelo existente; permisos `viewer`/`editor`/`owner` vía `require_kb_access`.
  - [x] ~~endpoints:~~
    - [x] ~~`GET /api/kbs`~~
    - [x] ~~`POST /api/kbs`~~
    - [x] ~~`GET /api/kbs/{kb_id}`~~
    - [x] ~~`PATCH /api/kbs/{kb_id}`~~
    - [x] ~~`DELETE /api/kbs/{kb_id}` (soft delete)~~
  - [x] ~~autorización:~~
    - [x] ~~validar acceso por KB en cada endpoint~~
  - [x] ~~eventos/auditoría:~~
    - [x] ~~`KB_CREATED`, `KB_UPDATED`, `KB_DELETED`~~
- [x] ~~Frontend:~~
  - [x] ~~vista lista KB~~ — `/kbs`
  - [x] ~~crear/editar/eliminar KB~~
  - [x] ~~selector de KB activo~~ — inicio + botón «Usar como activa» en `/kbs` (`localStorage`)
  - [x] ~~estados vacíos y errores claros (en español)~~
- [x] ~~Testing:~~
  - [x] ~~tests CRUD KB~~ — `tests/test_kb_integration.py` (con `TEST_DATABASE_URL`)
  - [x] ~~tests autorización (no acceder KB ajena)~~ — mismo archivo (403 sin membresía; viewer sin PATCH)

---

## Fase 4 — Uploads y pipeline de ingesta (async)

## Feature: uploads + ingestion

### Feature branch: `feat/uploads-api`

- [x] ~~Backend:~~
  - [x] ~~endpoint upload:~~
    - [x] ~~`POST /api/kbs/{kb_id}/documents/upload`~~
    - [x] ~~validación `kb_id` + permisos~~
    - [x] ~~validación de MIME (allowlist)~~
    - [x] ~~validación magic bytes (preferido)~~
    - [x] ~~límite tamaño (MB)~~
    - [x] ~~calcular `sha256` para deduplicación~~
    - [x] ~~storage seguro:~~
      - [x] ~~generar nombre UUID~~
      - [x] ~~evitar path traversal~~
      - [x] ~~guardar fuera del web root~~
  - [x] ~~endpoints docs:~~
    - [x] ~~`GET /api/kbs/{kb_id}/documents`~~
    - [x] ~~`GET /api/kbs/{kb_id}/documents/{doc_id}`~~
    - [x] ~~`GET /api/kbs/{kb_id}/documents/{doc_id}/status`~~
    - [x] ~~`GET /api/kbs/{kb_id}/documents/{doc_id}/file` (stream autenticado; `Content-Disposition` inline/attachment)~~
    - [x] ~~`DELETE /api/kbs/{kb_id}/documents/{doc_id}`~~
  - [x] ~~modelo `Document` con estados:~~
    - [x] ~~`UPLOADED`, `PROCESSING`, `READY`, `FAILED`, `QUARANTINED`, `DELETED`~~
  - [x] ~~encolar job Celery al upload:~~
    - [x] ~~`ingest_document(document_id)` (stub; pipeline en `feat/ingestion-worker`)~~
- [x] ~~Frontend:~~
  - [x] ~~componente upload (drag&drop)~~ — `DocumentUploadZone` en `/kbs/[kbId]/documents`
  - [x] ~~validación client-side (tamaño/tipo) como UX, no seguridad~~ — `upload-config.ts` + `validateClientFile`
  - [x] ~~progreso:~~
    - [x] ~~mostrar documentos y estatus~~
    - [x] ~~polling o socket para status updates~~ — polling 5 s si hay `UPLOADED`/`PROCESSING` y opción «Auto-actualizar»
  - [x] ~~metadatos:~~
    - [x] ~~tags~~
    - [x] ~~source~~
    - [x] ~~language~~
- [x] ~~Docker:~~
  - [x] ~~volumen `uploads` persistente (`rag_vol_uploads` en `worker`; `UPLOAD_STORAGE_DIR` en backend local)~~
  - [x] ~~permisos y ownership (WSL)~~ — Guía y comprobaciones manuales en `docs/13-troubleshooting.md` (uploads / `rag_vol_uploads`).
- [x] ~~Testing:~~
  - [x] ~~tests upload OK (pdf/docx/txt)~~ — PDF en `tests/test_documents_integration.py`; docx/txt cubiertos por MIME + magic en código
  - [x] ~~tests upload invalid mime~~
  - [x] ~~tests upload oversized~~
  - [x] ~~tests delete doc (soft delete)~~

### Feature branch: `feat/ingestion-worker`

- [x] ~~Worker (Celery):~~
  - [x] ~~colas separadas:~~
    - [x] ~~`ingest`~~
    - [x] ~~`ocr`~~
    - [x] ~~`embed`~~
  - [x] ~~pipeline por etapas con métricas:~~
    - [x] ~~antivirus~~
    - [x] ~~parse~~
    - [x] ~~ocr (si aplica)~~
    - [x] ~~normalize~~
    - [x] ~~chunk~~
    - [x] ~~embed~~
    - [x] ~~qdrant_upsert~~
  - [x] ~~reintentos:~~
    - [x] ~~backoff y número máximo~~
    - [x] ~~marcar FAILED con `error_code`~~
  - [x] ~~idempotencia:~~
    - [x] ~~evitar doble indexado si se reintenta (no reprocesar cuando ya está `READY` con chunks)~~
- [x] ~~Backend:~~
  - [x] ~~endpoint/servicio para reintentar ingesta (opcional):~~
    - [x] ~~`POST /api/kbs/{kb_id}/documents/{doc_id}/reindex`~~
- [x] ~~Testing:~~
  - [x] ~~test de transición de estados~~ — `tests/test_ingestion_worker.py` (`test_ingest_success_state_transition`, idempotencia)
  - [x] ~~test de reintentos y errores controlados~~ — mismo archivo (`test_ingest_controlled_error_*`, `test_ingest_max_attempts_*`, reindex HTTP)

---

## Fase 5 — Parsing y OCR (document processing)

## Feature: document parsing

### Feature branch: `feat/doc-parsers`

- [x] ~~Implementar extractores:~~
  - [x] ~~PDF extractor (PyMuPDF):~~
    - [x] ~~texto por página~~
    - [x] ~~conteo páginas~~
    - [x] ~~detectar “poco texto” para disparar OCR~~ — `needs_ocr` + métrica `parse_needs_ocr` (OCR real en `feat/ocr-tesseract`).
  - [x] ~~DOCX extractor (python-docx):~~
    - [x] ~~extraer títulos/párrafos~~
  - [x] ~~TXT extractor:~~
    - [x] ~~detectar encoding~~ — `charset-normalizer` + UTF-8 / Latin-1.
    - [x] ~~normalización básica~~ — `app/services/parsing/normalize.py`.
- [x] ~~Integrar Unstructured (si aplica):~~
  - [x] ~~particionado semántico~~ — fallback opcional (`UNSTRUCTURED_ENABLED=true` + paquete instalado aparte).
  - [x] ~~limpieza adicional~~ — vía partición Unstructured cuando el primario falla o devuelve poco texto.
- [x] ~~Manejo de errores:~~
  - [x] ~~errores recuperables vs fatales~~ — `RecoverableParserError` / `FatalParserError`.
  - [x] ~~timeouts por parser~~ — `PARSE_TIMEOUT_SECONDS`.
- [x] ~~Persistencia (opcional):~~
  - [x] ~~guardar `document_artifacts` (extracted/normalized)~~ — en disco `uploads/{kb_id}/artifacts/{doc_id}/` (`PARSER_SAVE_ARTIFACTS`).
- [x] ~~Tests:~~
  - [x] ~~PDFs con texto normal~~
  - [x] ~~PDFs con caracteres especiales (acentos)~~
  - [x] ~~DOCX con listas/headers~~
  - [x] ~~TXT con latin1~~

## Feature: OCR

### Feature branch: `feat/ocr-tesseract`

- [x] ~~OCR:~~
  - [x] ~~detectar cuándo se requiere OCR (threshold de texto)~~ — `needs_ocr` + `page_needs_ocr` / `document_needs_ocr`.
  - [x] ~~extraer imágenes/páginas~~ — rasterizado PyMuPDF (PNG por página).
  - [x] ~~ejecutar Tesseract con `spa`~~ — `pytesseract` + `OCR_TESSERACT_LANG=spa`.
  - [x] ~~juntar texto OCR con metadatos de página~~ — `PageText.ocr_applied`, merge `[OCR]` en texto.
- [x] ~~Performance:~~
  - [x] ~~limitar OCR a N páginas (configurable)~~ — `OCR_MAX_PAGES`.
  - [x] ~~concurrencia OCR dedicada~~ — `ThreadPoolExecutor` (`OCR_MAX_WORKERS`) + cola Celery `ocr` (`app.tasks.ocr`).
  - [x] ~~cache por hash de página/imagen (opcional)~~ — `uploads/.ocr_cache/` (`OCR_CACHE_ENABLED`).
- [x] ~~Tests:~~
  - [x] ~~PDF escaneado (fixtures)~~ — `tests/test_ocr.py` (mock Tesseract).
  - [x] ~~páginas mixtas (texto+imagen)~~ — mismo archivo (`test_mixed_pdf_only_low_text_pages_ocr`).

---

## Fase 6 — Chunking y embeddings

## Feature: chunking

### Feature branch: `feat/chunking-engine`

- [x] ~~Implementar chunking:~~
  - [x] ~~ventana deslizante con overlap (baseline)~~ — `app/services/chunking/engine.py` (`tokenizer` + ventana por tokens).
  - [x] ~~unir chunks muy pequeños~~ — fusión iterativa bajo `CHUNK_MIN_MERGE_TOKENS` (default 50).
  - [x] ~~preservar metadatos (página/sección)~~ — `page_start`/`page_end`/`section` desde `ParsedDocument.pages`.
- [x] ~~Config:~~
  - [x] ~~`CHUNK_SIZE_TOKENS`~~ — `app/core/config.py`.
  - [x] ~~`CHUNK_OVERLAP_TOKENS`~~
  - [x] ~~`MAX_CHUNK_SIZE_TOKENS`~~
  - [x] ~~hash de configuración para trazabilidad~~ — `chunking_config_hash` en metadata de cada chunk y métricas de ingesta.
- [x] ~~Tests:~~
  - [x] ~~chunking estable con acentos~~ — `tests/test_chunking.py`.
  - [x] ~~chunking en docs largos~~ — mismo archivo + aserciones en `test_ingestion_worker.py`.

## Feature: embeddings

### Feature branch: `feat/embeddings-bge-m3`

- [x] ~~Integrar Sentence Transformers:~~
  - [x] ~~cargar modelo `bge-m3`~~ — `app/services/embeddings/sentence_transformer.py` + extra `pip install -e '.[embeddings]'`.
  - [x] ~~batching~~ — `embed_texts` / `embed_document_chunks` con `EMBEDDING_BATCH_SIZE`.
  - [x] ~~normalización~~ — `EMBEDDING_NORMALIZE` (L2 en ST y fake).
- [x] ~~Robustez:~~
  - [x] ~~timeouts~~ — `EMBEDDING_TIMEOUT_SECONDS` por batch.
  - [x] ~~manejo de OOM (reducir batch)~~ — backoff hasta `EMBEDDING_BATCH_SIZE_MIN`.
  - [x] ~~colas de embeddings separadas~~ — `app.tasks.embed.embed_document_chunks` → cola `embed`.
- [x] ~~Trazabilidad:~~
  - [x] ~~persistir `embedding_model` en `chunks`~~ — `embedding_model_label` (`bge-m3`).
  - [x] ~~guardar `qdrant_point_id` en DB~~ — UUID del chunk (`stable_qdrant_point_id`).
- [x] ~~Tests:~~
  - [x] ~~embedding determinista para texto fijo (aprox)~~ — `tests/test_embeddings.py` (backend fake en `ENVIRONMENT=test`).
  - [x] ~~comportamiento con batching~~ — mismo archivo + ingesta en `test_ingestion_worker.py`.

---

## Fase 7 — Qdrant (vector store) e indexado

## Feature: qdrant integration

### Feature branch: `feat/qdrant-collection-v1`

- [x] ~~Crear/asegurar colección:~~
  - [x] ~~nombre `rag_chunks_v1`~~ — `QDRANT_COLLECTION` + `ensure_collection` en `app/services/qdrant/collection.py`.
  - [x] ~~distance metric (cosine)~~ — `Distance.COSINE` al crear colección.
  - [x] ~~payload schema (documentado)~~ — `app/services/qdrant/payload.py` + `docs/10-database-schema.md`.
- [x] ~~Upsert:~~
  - [x] ~~generar `point_id` estable (uuid o compuesto)~~ — UUID del chunk (`stable_qdrant_point_id`).
  - [x] ~~upsert por chunk con payload completo:~~
    - [x] ~~`kb_id`, `doc_id`, `chunk_id`~~
    - [x] ~~`tags`, `source`, `mime_type`, `language`~~
    - [x] ~~`page_start`, `page_end`, `chunk_index`~~
    - [x] ~~snippet `text` (opcional)~~ — `QDRANT_SNIPPET_MAX_CHARS`.
- [x] ~~Delete:~~
  - [x] ~~borrar por `doc_id` cuando se elimina documento~~ — `delete_document_vectors` en soft delete.
  - [x] ~~consistencia con soft delete Postgres~~ — filtro `kb_id` + `doc_id`; warning si Qdrant no responde.
- [x] ~~Tests:~~
  - [x] ~~upsert + search básico~~ — `tests/test_qdrant_integration.py` (con `TEST_QDRANT_URL`).
  - [x] ~~filtro por `kb_id`~~ — mismo archivo.
  - [x] ~~delete por filtro~~ — mismo archivo.

---

## Fase 8 — Retrieval híbrido + reranking

## Feature: retrieval

### Feature branch: `feat/retrieval-hybrid`

- [x] ~~Vector retrieval:~~
  - [x] ~~query embeddings (usar mismo modelo)~~ — `embed_texts` + `search_chunks` en `hybrid.py`.
  - [x] ~~Qdrant search con filtros `kb_id` server-side~~ — `search_chunks` (filtro obligatorio por KB).
  - [x] ~~topK configurable~~ — `RAG_VECTOR_TOP_K` / `top_k` en request.
- [x] ~~BM25:~~
  - [x] ~~definir estrategia:~~
    - [x] ~~índice por KB en memoria (MVP) o~~ — `app/services/retrieval/bm25_index.py`.
    - [ ] índice persistente (futuro)
  - [x] ~~construir índice al finalizar ingesta~~ — etapa `bm25_index` en `ingest.py` + refresh en soft delete.
  - [x] ~~query BM25 topK configurable~~ — `RAG_BM25_TOP_K`.
- [x] ~~Fusión:~~
  - [x] ~~implementar RRF o weighted score~~ — `reciprocal_rank_fusion` en `fusion.py`.
  - [x] ~~logging de scores para debug~~ — `log_fusion_debug` (nivel DEBUG).
- [x] ~~Metadata filtering:~~
  - [x] ~~tags~~
  - [x] ~~mime_type~~
  - [x] ~~source~~
- [x] ~~Endpoint opcional `/search` para debug~~ — `POST /api/kbs/{kb_id}/search` (`search.py`).
- [x] ~~Tests:~~
  - [x] ~~queries con nombres propios (mejoran por BM25)~~ — `test_retrieval_unit.py`.
  - [x] ~~queries semánticas (mejoran por vector)~~ — cubierto con `TEST_QDRANT_URL` opcional en integración.
  - [x] ~~filtros por tags~~ — `test_retrieval_integration.py`.

## Feature: reranking

### Feature branch: `feat/rerank-flashrank`

- [x] ~~Integrar FlashRank:~~
  - [x] ~~rerank de top-N a top-M~~ — `rag_rerank_candidate_top_k` → `rag_rerank_top_k` en `rerank.py` + `hybrid_search`.
  - [x] ~~métricas de latencia~~ — `RerankMetrics` + `metrics` en respuesta `POST /search`.
  - [x] ~~fallbacks si reranker falla (usar ranking previo)~~ — `status=fallback` conserva orden híbrido.
- [x] ~~Tests:~~
  - [x] ~~rerank no rompe cuando hay pocos candidatos~~ — `tests/test_rerank_unit.py`.

---

## Fase 9 — Chat RAG con streaming y citas

## Feature: chat

### Feature branch: `feat/chat-models`

- [x] ~~DB:~~
  - [x] ~~modelos `chats`, `chat_messages`, `message_citations`~~ — ORM en `app/models/chat.py` + migración inicial.
  - [x] ~~endpoints:~~
    - [x] ~~`POST /api/kbs/{kb_id}/chats`~~ — `app/api/routes/chats.py`.
    - [x] ~~`GET /api/kbs/{kb_id}/chats`~~
    - [x] ~~`GET /api/kbs/{kb_id}/chats/{chat_id}`~~
    - [x] ~~`GET /api/kbs/{kb_id}/chats/{chat_id}/messages`~~ — citas con `viewer_path` / `file_path` derivados en servidor.
- [x] ~~Tests CRUD chat y autorización por KB~~ — `tests/test_chat_integration.py`, `tests/test_chat_paths.py`, `scripts/test-chat.sh`.

### Feature branch: `feat/chat-rag-generation`

- [x] ~~Integración con Ollama:~~
  - [x] ~~wrapper cliente (timeouts, retries)~~ — `app/services/ollama/client.py`.
  - [x] ~~streaming tokens~~ — `chat_completion_stream` (Socket.IO en rama siguiente).
  - [x] ~~selección de modelo desde `.env`~~ — `LLM_MODEL` + `CHAT_LLM_BACKEND` (fake en test).
- [x] ~~Prompting:~~
  - [x] ~~system prompt “siempre en español”~~ — `app/services/chat/prompting.py`.
  - [x] ~~grounding: si no hay evidencia, decirlo~~ — respuesta sin hits + fake/Ollama.
  - [x] ~~formato de salida con fuentes~~ — sección **Fuentes:** en prompt y fake.
- [x] ~~Citas:~~
  - [x] ~~backend asigna citas basadas en chunks usados~~ — hits de `hybrid_search`.
  - [x] ~~persistir `message_citations` (`page_start` / `page_end` alineados con `chunks`)~~ — `generation.py`.
  - [x] ~~en respuesta API y evento `chat:citation`~~ — API `POST /messages` con `viewer_path` / `file_path`; evento socket en `feat/chat-streaming-socketio`.
- [x] ~~Endpoint:~~
  - [x] ~~`POST /api/kbs/{kb_id}/chats/{chat_id}/messages`~~ — `stream=false` → 200; `stream=true` → 202 ack.
- [x] ~~Tests:~~
  - [x] ~~sin contexto → respuesta “no evidencia”~~ — `test_chat_generation_integration.py`.
  - [x] ~~con contexto → incluye citas~~ — mismo archivo + BM25.

### Feature branch: `feat/chat-streaming-socketio`

- [x] ~~Backend:~~
  - [x] ~~Socket.IO namespace `/chat`~~ — `app/realtime/` + `asgi_application` en `main.py`.
  - [x] ~~auth handshake con JWT~~ — `app/realtime/auth.py` (auth payload o `?token=`).
  - [x] ~~rooms por `chat_id`~~ — `chat:join` → room `chat:{chat_id}`.
  - [x] ~~eventos:~~
    - [x] ~~`chat:join`~~
    - [x] ~~`chat:token`~~
    - [x] ~~`chat:citation`~~
    - [x] ~~`chat:done`~~
    - [x] ~~`ingest:progress`~~ — `ingest:join` + `emit_ingest_progress`.
- [x] ~~Frontend:~~
  - [x] ~~cliente Socket.IO~~ — `frontend/src/lib/socket-client.ts`.
  - [x] ~~UI streaming (render incremental)~~ — `frontend/src/app/kbs/[kbId]/chats/[chatId]/page.tsx`.
  - [x] ~~reconexión y manejo de errores~~ — opciones `reconnection` en cliente.
- [x] ~~Proxy:~~
  - [x] ~~Traefik enruta `/socket.io`~~ — `docker/traefik/dynamic/bootstrap.yml`.
- [x] ~~Tests:~~
  - [x] ~~test de conexión auth~~ — `tests/test_socketio_auth.py`.
  - [x] ~~test de streaming básico (manual)~~ — `tests/test_socketio_streaming.py` + `scripts/test-socketio.sh`.

---

## Fase 10 — Seguridad avanzada (WAF, Fail2ban, antivirus, prompt injection)

## Feature: antivirus uploads

### Feature branch: `feat/security-clamav`

- [x] ~~Docker:~~
  - [x] ~~agregar servicio `clamav` (clamd)~~ — perfil `clamav`, puerto `127.0.0.1:3310`.
  - [x] ~~healthcheck~~ — `clamdcheck.sh`, `start_period` 300s.
- [x] ~~Worker:~~
  - [x] ~~integrar escaneo antes de parse~~ — `app/services/antivirus/` + etapa `antivirus` en `ingest.py`.
  - [x] ~~cuarentena:~~
    - [x] ~~mover archivo a `uploads/quarantine/`~~ — `quarantine.py`.
    - [x] ~~marcar doc `QUARANTINED`~~
  - [x] ~~registrar `security_event` con hash y firma~~ — `DOCUMENT_QUARANTINED`.
- [x] ~~Backend/Frontend:~~
  - [x] ~~mostrar estado “en cuarentena”~~ — badge y bloqueo descarga (ya en API).
  - [x] ~~UI mensajes claros en español~~ — `documents/page.tsx`.
- [x] ~~Tests:~~
  - [x] ~~prueba con archivo EICAR (si se autoriza en entorno)~~ — `test_clamav_unit.py`, `test_ingestion_worker.py`, `test_clamav_integration.py` + `scripts/test-clamav.sh`.

## Feature: WAF

### Feature branch: `feat/security-waf-modsecurity`

- [x] ~~Docker:~~
  - [x] ~~contenedor ModSecurity + OWASP CRS~~ — `owasp/modsecurity-crs:4-nginx-alpine` en `docker-compose.waf.yml` (perfil `waf`).
  - [x] ~~routing Traefik → WAF → backend~~ — `bootstrap-waf.yml`; `/socket.io` directo al backend.
  - [x] ~~modo inicial `DetectionOnly`~~ — `WAF_MODE` → `MODSEC_RULE_ENGINE`.
  - [x] ~~logging de eventos WAF a Loki~~ — audit JSON stdout + Promtail (`logging.promtail=true`).
- [x] ~~Ajustes:~~
  - [x] ~~excepciones mínimas para uploads (sin abrir demasiado)~~ — `docker/waf/REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf`.
  - [x] ~~límites de body size~~ — `MAX_FILE_SIZE` / `MODSEC_REQ_BODY_LIMIT` = `WAF_MAX_BODY_BYTES` (50 MB).
- [x] ~~Tests:~~
  - [x] ~~requests con payload XSS/SQLi bloqueados~~ — `scripts/test-waf.sh`, `tests/test_waf_integration.py` (con `WAF_MODE=On`).

## Feature: rate limiting

### Feature branch: `feat/security-rate-limits`

- [x] ~~Traefik:~~
  - [x] ~~middleware rate limit por IP~~ — `rag-ratelimit-api` (200/min) en `bootstrap.yml` / `bootstrap-waf.yml`.
  - [x] ~~policy específica `/api/auth/login`~~ — router `rag-auth-login` + `rag-ratelimit-login` (10/min).
- [x] ~~Backend:~~
  - [x] ~~rate limit por usuario (Redis)~~ — `UserRateLimitMiddleware` + `APP_RATE_LIMIT_*`.
  - [x] ~~quotas para ingesta (docs/min)~~ — `check_ingest_upload_quota` en upload (`INGEST_UPLOAD_MAX_*`).
- [x] ~~Auditoría:~~
  - [x] ~~persistir `rate_limit_events`~~ — `rate_limit_audit.py` + middleware/rutas auth/upload.
- [x] ~~Tests:~~
  - [x] ~~rebasar límite → 429~~ — `tests/test_rate_limit_unit.py`, `tests/test_rate_limit_integration.py`, `scripts/test-rate-limits.sh`.

## Feature: Fail2ban

### Feature branch: `feat/security-fail2ban`

- [x] ~~Definir estrategia:~~
  - [x] ~~leer logs de Traefik/WAF/Backend~~ — `docs/17-fail2ban.md`; Traefik `access.log`, backend `SECURITY_ACCESS`.
  - [x] ~~patrones: múltiples 401/403/login fail~~ — `docker/fail2ban/data/filter.d/`.
- [x] ~~Docker:~~
  - [x] ~~contenedor fail2ban (si viable en WSL2) o documentación para host-level~~ — perfil `fail2ban` + `banaction=dummy` (WSL); iptables en Linux en doc.
- [x] ~~Tests:~~
  - [x] ~~simulación de brute-force (manual) y bloqueo de IP (local)~~ — `scripts/test-fail2ban.sh`, `tests/test_fail2ban_filters.py`.

## Feature: prompt injection defense

### Feature branch: `feat/security-prompt-guards`

- [x] ~~Backend:~~
  - [x] ~~sanitización de chunks antes de prompt~~ — `app/services/chat/prompt_guards.py` (`sanitize_chunk_text`, etiqueta `[DOC:` en `prompting.py`).
  - [x] ~~heurística para detectar instrucciones maliciosas~~ — patrones es/en en chunks y consulta.
  - [x] ~~excluir chunks sospechosos del contexto~~ — `filter_search_hits` en `generation.py` y `streaming.py`.
  - [x] ~~registrar `safety_flags` en mensaje~~ — JSONB en `ChatMessage` + API `safety_flags`.
- [x] ~~UX:~~
  - [x] ~~mostrar aviso “contenido potencialmente malicioso fue ignorado” (opcional)~~ — banner ámbar en `frontend/.../chats/[chatId]/page.tsx` si `user_notice`.
- [x] ~~Tests:~~
  - [x] ~~documento con “ignora instrucciones” no domina la respuesta~~ — `tests/test_prompt_guards_integration.py`.
  - [x] ~~query de exfiltración es rechazada~~ — mismo + `tests/test_prompt_guards_unit.py`, `scripts/test-prompt-guards.sh`.

---

## Fase 11 — Observabilidad (Prometheus, Grafana, Loki)

## Feature: observability

### Feature branch: `feat/observability-metrics`

- [x] ~~Backend:~~
  - [x] ~~exponer `/metrics` (Prometheus)~~ — `app/main.py` + `prometheus-client`; middleware HTTP en `prometheus_middleware.py`.
  - [x] ~~métricas por etapa:~~
    - [x] ~~ingest parse/ocr/embed/upsert~~ — `app/observability/metrics.py` + etapas en `ingest.py`; exporter worker en `celery_app.py`.
    - [x] ~~retrieval vector/bm25/rerank~~ — `hybrid.py`, `rerank.py`.
    - [x] ~~chat first-token/total~~ — `generation.py`, `streaming.py`.
  - [x] ~~labels: `kb_id` (cuidado privacidad), `status`, `endpoint`~~ — `status`/`endpoint` en HTTP e ingesta; `kb_id` deshabilitado por defecto (`PROMETHEUS_INCLUDE_KB_ID_LABEL=false`).
- [x] ~~Docker:~~
  - [x] ~~prometheus config para scrape~~ — `docker/observability/prometheus.yml` (Traefik + `host.docker.internal:8000/8001`).
  - [x] ~~grafana datasource prometheus/loki~~ — UIDs fijos + URL con prefijo `/prometheus`.
- [x] ~~Dashboards:~~
  - [x] ~~latencia API~~ — `rag-overview.json` (p95 por endpoint).
  - [x] ~~tasa de errores~~ — panel ratio 5xx.
  - [x] ~~duración ingesta por etapa~~ — `rag_ingest_stage_duration_seconds`.
  - [x] ~~throughput de embeddings~~ — `rag_embeddings_processed_total`.
- [x] ~~Tests:~~
  - [x] ~~verificar scrape y paneles visibles~~ — `tests/test_prometheus_metrics.py` + `scripts/test-observability.sh`.

### Feature branch: `feat/observability-logs`

- [x] ~~Logs:~~
  - [x] ~~formato estructurado~~ — JSON en `logging_config.py` + `http_access` en `access_log_middleware.py`.
  - [x] ~~correlación por `request_id`, `document_id`, `chat_id`~~ — `log_context.py`, `correlation_middleware.py`, ingesta/worker.
- [x] ~~Loki:~~
  - [x] ~~promtail o driver para enviar logs~~ — `promtail-config.yml` (Docker labels + `uploads/logs/*.jsonl`); labels en compose.
  - [x] ~~queries guardadas para debugging~~ — dashboard `rag-logs.json` + panel de queries en Grafana.
- [x] ~~Alertas (opcional):~~
  - [x] ~~reglas simples: alta tasa de 5xx, dependencia caída~~ — `docker/observability/prometheus/rules/alerts.yml`.

---

## Fase 12 — Frontend UX completa (KB, docs, chat, citas)

## Feature: frontend shell

### Feature branch: `feat/frontend-layout`

- [ ] Layout:
  - [ ] navegación (KB selector)
  - [ ] sidebar de documentos
  - [ ] panel de chat
- [ ] Estados:
  - [ ] loading
  - [ ] empty
  - [ ] error
- [ ] i18n (mínimo):
  - [ ] strings en español centralizados

## Feature: documents UI

### Feature branch: `feat/frontend-documents`

- [ ] Lista de documentos con filtros:
  - [ ] status
  - [ ] tags
  - [ ] source
  - [ ] tipo
- [ ] Detalle de documento:
  - [ ] metadatos
  - [ ] estado de ingesta por etapas
  - [ ] botón reindex (si existe)
- [ ] **Visor con salto a página (PDF):**
  - [ ] ruta p. ej. `/kbs/[kbId]/documents/[docId]?page=N`
  - [ ] integrar **PDF.js**; obtener PDF con `Authorization` (fetch) y pasar a visor
  - [ ] DOCX/TXT: descarga o vista texto; sin prometer página exacta salvo conversión futura a PDF
- [ ] Upload:
  - [ ] drag&drop
  - [ ] validación UX
  - [ ] progreso de ingesta (socket o polling)

## Feature: chat UI

### Feature branch: `feat/frontend-chat`

- [ ] Vista chat:
  - [ ] streaming tokens
  - [ ] render Markdown seguro
  - [ ] scroll behavior (autoscroll inteligente)
- [ ] Citas:
  - [ ] mostrar fuentes como lista con hipervínculos a `viewer_path` (y opción descarga `file_path`)
  - [ ] al hacer click, abrir visor en página cuando `mime_type` sea PDF y exista `page_start`
- [ ] Historial:
  - [ ] lista de chats por KB
  - [ ] renombrar chat (opcional)

---

## Fase 13 — Testing y calidad

## Feature: backend testing

### Feature branch: `test/backend-suite`

- [ ] Unit tests:
  - [ ] auth/jwt
  - [ ] chunking
  - [ ] sanitización prompt injection
- [ ] Integration tests:
  - [ ] endpoints principales (auth, KB, upload, chat)
  - [ ] pipeline Celery básico (con mocks o infraestructura)
- [ ] Contract tests:
  - [ ] asegurar que responses cumplen `09-api-spec.md`

## Feature: frontend testing

### Feature branch: `test/frontend-suite`

- [ ] Tests de componentes:
  - [ ] login form
  - [ ] uploader
  - [ ] message renderer (markdown + citations)
- [ ] E2E (opcional):
  - [ ] flujo: login → crear KB → subir doc → preguntar → ver citas

---

## Fase 14 — Integración Docker (stack real, sustitución de placeholders)

**Objetivo:** poder levantar **backend FastAPI**, **worker Celery**, **frontend Next.js** y dependencias (Postgres, Redis, Qdrant, Ollama, Traefik) con `docker compose up`, con variables de entorno coherentes para **local**, **test** y **prod**, y pruebas manuales (UI + Swagger) y automáticas (smoke).

**Contexto actual:** Fase 0 dejó `frontend`, `backend` y `worker` como **placeholders** (`docker/placeholders/*`). Esta fase los reemplaza por imágenes del código en `backend/` y `frontend/`.

**Orden sugerido de ramas:** backend/worker → frontend → compose/env → perfiles test/prod → smoke/CI.

---

## Feature: imágenes backend y worker

### Feature branch: `chore/docker-backend-worker`

- [ ] Docker:
  - [ ] `docker/backend/Dockerfile` (multi-stage: deps + runtime, usuario no-root)
  - [ ] `docker/worker/Dockerfile` (misma base que API + comando Celery)
  - [ ] `.dockerignore` en `backend/` (venv, `__pycache__`, tests, `.env`)
- [ ] Backend (servicio `backend` en compose):
  - [ ] sustituir build `docker/placeholders/backend` por imagen real
  - [ ] comando: `uvicorn` (o gunicorn+uvicorn workers en prod)
  - [ ] `depends_on` Postgres/Redis con `condition: service_healthy`
  - [ ] variables: `DATABASE_URL`, `REDIS_*`, `JWT_*`, `UPLOAD_STORAGE_DIR`, `CORS_*`, parsing/Celery
  - [ ] volumen compartido `rag_vol_uploads` montado en `/uploads` (misma ruta que worker)
  - [ ] healthcheck HTTP: `GET /api/health` (503 si dependencia cae)
  - [ ] exponer Swagger/OpenAPI en Traefik (`/api/docs`, `/api/openapi.json`)
- [ ] Worker (servicio `worker`):
  - [ ] sustituir placeholder `sleep infinity` por worker Celery real
  - [ ] colas `ingest`, `ocr`, `embed` (misma config que local)
  - [ ] mismo volumen `/uploads` y mismas envs de DB/Redis/Qdrant/Ollama que el API
  - [ ] healthcheck ligero (proceso Celery o script `celery inspect ping`)
- [ ] Migraciones:
  - [ ] documentar o automatizar `alembic upgrade head` al arranque (entrypoint opcional) o paso manual en `01-deployment.md`
  - [ ] seed dev opcional (`scripts/seed_dev_user.py`) solo en perfil `local`
- [ ] Deprecación:
  - [ ] marcar `docker/placeholders/backend` y `docker/placeholders/worker` como legacy o eliminar tras validar stack

---

## Feature: imagen frontend

### Feature branch: `chore/docker-frontend`

- [ ] Docker:
  - [ ] `docker/frontend/Dockerfile` (build Next.js `standalone` + runtime mínimo)
  - [ ] `.dockerignore` en `frontend/` (`node_modules`, `.next`, `.env*`)
- [ ] Frontend (servicio `frontend`):
  - [ ] sustituir build `docker/placeholders/frontend`
  - [ ] build-args / env: `NEXT_PUBLIC_API_BASE_URL` (p. ej. `http://localhost/api`)
  - [ ] healthcheck: `GET /` o ruta `/health` si se añade
  - [ ] labels Traefik: `PathPrefix(`/`)` con prioridad menor que `/api`
- [ ] Deprecación:
  - [ ] marcar `docker/placeholders/frontend` como legacy o eliminar tras validar stack

---

## Feature: Compose integrado (red, volúmenes, Traefik)

### Feature branch: `chore/docker-compose-real-stack`

- [ ] `docker-compose.yml` (o `compose.yaml`):
  - [ ] servicios reales referencian `docker/backend`, `docker/worker`, `docker/frontend`
  - [ ] red `rag_net` sin cambios; solo Traefik publica `80/443` al host
  - [ ] volúmenes: `rag_vol_postgres`, `rag_vol_uploads`, `rag_vol_qdrant`, `rag_vol_ollama` (y opcionales clamav/observability)
  - [ ] **no** publicar puertos de Postgres/Redis en prod (mantener `127.0.0.1` solo en perfil `local` / override)
- [ ] Traefik:
  - [ ] rutas: `/` → frontend, `/api` → backend (incl. WebSocket futuro `/socket.io`)
  - [ ] timeouts y límites de body alineados con `MAX_UPLOAD_MB`
- [ ] Envs:
  - [ ] alinear `.env.example` raíz con nombres de servicio Docker (`postgres`, `redis`, `qdrant`, `ollama`)
  - [ ] documentar `UPLOAD_STORAGE_DIR=/uploads` en API y worker
  - [ ] `CELERY_BROKER_URL=redis://redis:6379/0` dentro de la red compose
- [ ] Arranque:
  - [ ] `docker compose up -d --build` levanta stack usable sin `npm run dev` ni uvicorn en host
  - [ ] orden: infra (postgres, redis) → migrate → backend + worker → frontend
- [ ] Docs (mínimo en esta rama):
  - [ ] actualizar `docs/02-smoke-test.md` (dejar de asumir solo placeholders)
  - [ ] actualizar `docs/01-deployment.md` sección “backend real en compose”

---

## Feature: perfiles y entornos test / prod

### Feature branch: `chore/docker-profiles-test-prod`

- [ ] Archivos:
  - [ ] `docker-compose.override.yml.example` (local: puertos `5432`/`6379` al host, hot-reload opcional)
  - [ ] `docker-compose.test.yml` o perfil Compose `test` (DB `rag_test`, `ENVIRONMENT=test`, eager Celery si aplica)
  - [ ] `.env.production.example` / `.env.test.example` alineados con servicios por nombre DNS interno
- [ ] Test:
  - [ ] `TEST_DATABASE_URL` apuntando a Postgres del compose (perfil test) para pytest en host o contenedor `backend-test`
  - [ ] documentar ejecución: `docker compose --profile test run --rm backend pytest …`
- [ ] Prod (local “production-like”):
  - [ ] sin bind mounts de código; solo volúmenes nombrados
  - [ ] secretos largos obligatorios (`JWT_SECRET`, `PASSWORD_PEPPER`)
  - [ ] `LOG_LEVEL=WARNING`, CORS restringido
- [ ] CI (opcional en esta rama o en `test/docker-stack-smoke`):
  - [ ] job GitHub Actions: `compose up` + health + pytest smoke

---

## Feature: smoke y validación del stack Docker

### Feature branch: `test/docker-stack-smoke`

- [ ] Scripts:
  - [ ] `scripts/docker-smoke.sh`: compose up, esperar health, curl `/api/health`, `/`, login opcional
  - [ ] exit code distinto de 0 si falla alguna dependencia crítica
- [ ] Testing automático:
  - [ ] tests de integración ejecutables contra API en `http://localhost/api` (variable `SMOKE_BASE_URL`)
  - [ ] o contenedor one-shot que corre subset de pytest con `TEST_DATABASE_URL` interno
- [ ] Manual (checklist en `docs/02-smoke-test.md`):
  - [ ] Swagger: `http://localhost/api/docs` — login, CRUD KB, upload PDF
  - [ ] UI: `http://localhost/` — login, subir documento, ver estado ingesta
  - [ ] worker: documento pasa a `READY` (o `FAILED` con error legible)
- [ ] Limpieza:
  - [ ] `scripts/docker-smoke-down.sh` o documentar `docker compose down` / `down -v`

---

## Fase 15 — Documentación y scripts operativos

## Feature: scripts

### Feature branch: `chore/scripts-ops`

- [ ] Script backup Postgres:
  - [ ] `scripts/backup_postgres.sh`
- [ ] Script backup uploads:
  - [ ] `scripts/backup_uploads.sh`
- [ ] Script snapshot Qdrant (si se habilita):
  - [ ] `scripts/qdrant_snapshot.sh`
- [ ] Script reindex KB/doc:
  - [ ] `scripts/reindex.sh` (llama endpoint o ejecuta job)

## Feature: docs completeness

### Feature branch: `docs/finalize`

- [ ] Validar que docs reflejan implementación real:
  - [ ] `docs/09-api-spec.md`
  - [ ] `docs/10-database-schema.md`
  - [ ] `docs/11-rag-flow.md`
  - [ ] `docs/12-security.md`
  - [ ] `docs/01-deployment.md`
- [ ] Agregar ejemplos reales (capturas/logs) cuando exista implementación
- [ ] Agregar “operational playbooks” (incidentes comunes)

---

## Fase 16 — Performance tuning (local)

### Feature branch: `perf/ingestion-tuning`

- [ ] Medir:
  - [ ] parse vs OCR vs embed
  - [ ] tamaños de batch óptimos
- [ ] Optimizar:
  - [ ] reducir OCR innecesario
  - [ ] chunking más semántico para reducir tokens
  - [ ] caching de embeddings para duplicados
- [ ] Ajustar límites:
  - [ ] concurrencia Celery por cola
  - [ ] timeouts

### Feature branch: `perf/retrieval-tuning`

- [ ] Ajustar:
  - [ ] topK vector/BM25
  - [ ] rerank topK
  - [ ] estrategia de fusión (RRF/weights)
- [ ] Agregar métricas de calidad proxy:
  - [ ] porcentaje con citas
  - [ ] tiempo a primer token
