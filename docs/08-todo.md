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

- [ ] Worker (Celery):
  - [ ] colas separadas:
    - [ ] `ingest`
    - [ ] `ocr`
    - [ ] `embed`
  - [ ] pipeline por etapas con métricas:
    - [ ] antivirus
    - [ ] parse
    - [ ] ocr (si aplica)
    - [ ] normalize
    - [ ] chunk
    - [ ] embed
    - [ ] qdrant_upsert
  - [ ] reintentos:
    - [ ] backoff y número máximo
    - [ ] marcar FAILED con `error_code`
  - [ ] idempotencia:
    - [ ] evitar doble indexado si se reintenta
- [ ] Backend:
  - [ ] endpoint/servicio para reintentar ingesta (opcional):
    - [ ] `POST /api/kbs/{kb_id}/documents/{doc_id}/reindex`
- [ ] Testing:
  - [ ] test de transición de estados
  - [ ] test de reintentos y errores controlados

---

## Fase 5 — Parsing y OCR (document processing)

## Feature: document parsing

### Feature branch: `feat/doc-parsers`

- [ ] Implementar extractores:
  - [ ] PDF extractor (PyMuPDF):
    - [ ] texto por página
    - [ ] conteo páginas
    - [ ] detectar “poco texto” para disparar OCR
  - [ ] DOCX extractor (python-docx):
    - [ ] extraer títulos/párrafos
  - [ ] TXT extractor:
    - [ ] detectar encoding
    - [ ] normalización básica
- [ ] Integrar Unstructured (si aplica):
  - [ ] particionado semántico
  - [ ] limpieza adicional
- [ ] Manejo de errores:
  - [ ] errores recuperables vs fatales
  - [ ] timeouts por parser
- [ ] Persistencia (opcional):
  - [ ] guardar `document_artifacts` (extracted/normalized)
- [ ] Tests:
  - [ ] PDFs con texto normal
  - [ ] PDFs con caracteres especiales (acentos)
  - [ ] DOCX con listas/headers
  - [ ] TXT con latin1

## Feature: OCR

### Feature branch: `feat/ocr-tesseract`

- [ ] OCR:
  - [ ] detectar cuándo se requiere OCR (threshold de texto)
  - [ ] extraer imágenes/páginas
  - [ ] ejecutar Tesseract con `spa`
  - [ ] juntar texto OCR con metadatos de página
- [ ] Performance:
  - [ ] limitar OCR a N páginas (configurable)
  - [ ] concurrencia OCR dedicada
  - [ ] cache por hash de página/imagen (opcional)
- [ ] Tests:
  - [ ] PDF escaneado (fixtures)
  - [ ] páginas mixtas (texto+imagen)

---

## Fase 6 — Chunking y embeddings

## Feature: chunking

### Feature branch: `feat/chunking-engine`

- [ ] Implementar chunking:
  - [ ] ventana deslizante con overlap (baseline)
  - [ ] unir chunks muy pequeños
  - [ ] preservar metadatos (página/sección)
- [ ] Config:
  - [ ] `CHUNK_SIZE_TOKENS`
  - [ ] `CHUNK_OVERLAP_TOKENS`
  - [ ] `MAX_CHUNK_SIZE_TOKENS`
  - [ ] hash de configuración para trazabilidad
- [ ] Tests:
  - [ ] chunking estable con acentos
  - [ ] chunking en docs largos

## Feature: embeddings

### Feature branch: `feat/embeddings-bge-m3`

- [ ] Integrar Sentence Transformers:
  - [ ] cargar modelo `bge-m3`
  - [ ] batching
  - [ ] normalización
- [ ] Robustez:
  - [ ] timeouts
  - [ ] manejo de OOM (reducir batch)
  - [ ] colas de embeddings separadas
- [ ] Trazabilidad:
  - [ ] persistir `embedding_model` en `chunks`
  - [ ] guardar `qdrant_point_id` en DB
- [ ] Tests:
  - [ ] embedding determinista para texto fijo (aprox)
  - [ ] comportamiento con batching

---

## Fase 7 — Qdrant (vector store) e indexado

## Feature: qdrant integration

### Feature branch: `feat/qdrant-collection-v1`

- [ ] Crear/asegurar colección:
  - [ ] nombre `rag_chunks_v1`
  - [ ] distance metric (cosine)
  - [ ] payload schema (documentado)
- [ ] Upsert:
  - [ ] generar `point_id` estable (uuid o compuesto)
  - [ ] upsert por chunk con payload completo:
    - [ ] `kb_id`, `doc_id`, `chunk_id`
    - [ ] `tags`, `source`, `mime_type`, `language`
    - [ ] `page_start`, `page_end`, `chunk_index`
    - [ ] snippet `text` (opcional)
- [ ] Delete:
  - [ ] borrar por `doc_id` cuando se elimina documento
  - [ ] consistencia con soft delete Postgres
- [ ] Tests:
  - [ ] upsert + search básico
  - [ ] filtro por `kb_id`
  - [ ] delete por filtro

---

## Fase 8 — Retrieval híbrido + reranking

## Feature: retrieval

### Feature branch: `feat/retrieval-hybrid`

- [ ] Vector retrieval:
  - [ ] query embeddings (usar mismo modelo)
  - [ ] Qdrant search con filtros `kb_id` server-side
  - [ ] topK configurable
- [ ] BM25:
  - [ ] definir estrategia:
    - [ ] índice por KB en memoria (MVP) o
    - [ ] índice persistente (futuro)
  - [ ] construir índice al finalizar ingesta
  - [ ] query BM25 topK configurable
- [ ] Fusión:
  - [ ] implementar RRF o weighted score
  - [ ] logging de scores para debug
- [ ] Metadata filtering:
  - [ ] tags
  - [ ] mime_type
  - [ ] source
- [ ] Endpoint opcional `/search` para debug
- [ ] Tests:
  - [ ] queries con nombres propios (mejoran por BM25)
  - [ ] queries semánticas (mejoran por vector)
  - [ ] filtros por tags

## Feature: reranking

### Feature branch: `feat/rerank-flashrank`

- [ ] Integrar FlashRank:
  - [ ] rerank de top-N a top-M
  - [ ] métricas de latencia
  - [ ] fallbacks si reranker falla (usar ranking previo)
- [ ] Tests:
  - [ ] rerank no rompe cuando hay pocos candidatos

---

## Fase 9 — Chat RAG con streaming y citas

## Feature: chat

### Feature branch: `feat/chat-models`

- [ ] DB:
  - [ ] modelos `chats`, `chat_messages`, `message_citations`
  - [ ] endpoints:
    - [ ] `POST /api/kbs/{kb_id}/chats`
    - [ ] `GET /api/kbs/{kb_id}/chats`
    - [ ] `GET /api/kbs/{kb_id}/chats/{chat_id}`
    - [ ] `GET /api/kbs/{kb_id}/chats/{chat_id}/messages`
- [ ] Tests CRUD chat y autorización por KB

### Feature branch: `feat/chat-rag-generation`

- [ ] Integración con Ollama:
  - [ ] wrapper cliente (timeouts, retries)
  - [ ] streaming tokens
  - [ ] selección de modelo desde `.env`
- [ ] Prompting:
  - [ ] system prompt “siempre en español”
  - [ ] grounding: si no hay evidencia, decirlo
  - [ ] formato de salida con fuentes
- [ ] Citas:
  - [ ] backend asigna citas basadas en chunks usados
  - [ ] persistir `message_citations` (`page_start` / `page_end` alineados con `chunks`)
  - [ ] en respuesta API y evento `chat:citation`: incluir `viewer_path`, `file_path`, `filename_original`, `mime_type` (derivados en servidor; forma en `09-api-spec.md`)
- [ ] Endpoint:
  - [ ] `POST /api/kbs/{kb_id}/chats/{chat_id}/messages`
- [ ] Tests:
  - [ ] sin contexto → respuesta “no evidencia”
  - [ ] con contexto → incluye citas

### Feature branch: `feat/chat-streaming-socketio`

- [ ] Backend:
  - [ ] Socket.IO namespace `/chat`
  - [ ] auth handshake con JWT
  - [ ] rooms por `chat_id`
  - [ ] eventos:
    - [ ] `chat:join`
    - [ ] `chat:token`
    - [ ] `chat:citation`
    - [ ] `chat:done`
    - [ ] `ingest:progress`
- [ ] Frontend:
  - [ ] cliente Socket.IO
  - [ ] UI streaming (render incremental)
  - [ ] reconexión y manejo de errores
- [ ] Proxy:
  - [ ] Traefik enruta `/socket.io`
- [ ] Tests:
  - [ ] test de conexión auth
  - [ ] test de streaming básico (manual)

---

## Fase 10 — Seguridad avanzada (WAF, Fail2ban, antivirus, prompt injection)

## Feature: antivirus uploads

### Feature branch: `feat/security-clamav`

- [ ] Docker:
  - [ ] agregar servicio `clamav` (clamd)
  - [ ] healthcheck
- [ ] Worker:
  - [ ] integrar escaneo antes de parse
  - [ ] cuarentena:
    - [ ] mover archivo a `uploads/quarantine/`
    - [ ] marcar doc `QUARANTINED`
  - [ ] registrar `security_event` con hash y firma
- [ ] Backend/Frontend:
  - [ ] mostrar estado “en cuarentena”
  - [ ] UI mensajes claros en español
- [ ] Tests:
  - [ ] prueba con archivo EICAR (si se autoriza en entorno)

## Feature: WAF

### Feature branch: `feat/security-waf-modsecurity`

- [ ] Docker:
  - [ ] contenedor ModSecurity + OWASP CRS
  - [ ] routing Traefik → WAF → backend
  - [ ] modo inicial `DetectionOnly`
  - [ ] logging de eventos WAF a Loki
- [ ] Ajustes:
  - [ ] excepciones mínimas para uploads (sin abrir demasiado)
  - [ ] límites de body size
- [ ] Tests:
  - [ ] requests con payload XSS/SQLi bloqueados

## Feature: rate limiting

### Feature branch: `feat/security-rate-limits`

- [ ] Traefik:
  - [ ] middleware rate limit por IP
  - [ ] policy específica `/api/auth/login`
- [ ] Backend:
  - [ ] rate limit por usuario (Redis)
  - [ ] quotas para ingesta (docs/min)
- [ ] Auditoría:
  - [ ] persistir `rate_limit_events`
- [ ] Tests:
  - [ ] rebasar límite → 429

## Feature: Fail2ban

### Feature branch: `feat/security-fail2ban`

- [ ] Definir estrategia:
  - [ ] leer logs de Traefik/WAF/Backend
  - [ ] patrones: múltiples 401/403/login fail
- [ ] Docker:
  - [ ] contenedor fail2ban (si viable en WSL2) o documentación para host-level
- [ ] Tests:
  - [ ] simulación de brute-force (manual) y bloqueo de IP (local)

## Feature: prompt injection defense

### Feature branch: `feat/security-prompt-guards`

- [ ] Backend:
  - [ ] sanitización de chunks antes de prompt
  - [ ] heurística para detectar instrucciones maliciosas
  - [ ] excluir chunks sospechosos del contexto
  - [ ] registrar `safety_flags` en mensaje
- [ ] UX:
  - [ ] mostrar aviso “contenido potencialmente malicioso fue ignorado” (opcional)
- [ ] Tests:
  - [ ] documento con “ignora instrucciones” no domina la respuesta
  - [ ] query de exfiltración es rechazada

---

## Fase 11 — Observabilidad (Prometheus, Grafana, Loki)

## Feature: observability

### Feature branch: `feat/observability-metrics`

- [ ] Backend:
  - [ ] exponer `/metrics` (Prometheus)
  - [ ] métricas por etapa:
    - [ ] ingest parse/ocr/embed/upsert
    - [ ] retrieval vector/bm25/rerank
    - [ ] chat first-token/total
  - [ ] labels: `kb_id` (cuidado privacidad), `status`, `endpoint`
- [ ] Docker:
  - [ ] prometheus config para scrape
  - [ ] grafana datasource prometheus/loki
- [ ] Dashboards:
  - [ ] latencia API
  - [ ] tasa de errores
  - [ ] duración ingesta por etapa
  - [ ] throughput de embeddings
- [ ] Tests:
  - [ ] verificar scrape y paneles visibles

### Feature branch: `feat/observability-logs`

- [ ] Logs:
  - [ ] formato estructurado
  - [ ] correlación por `request_id`, `document_id`, `chat_id`
- [ ] Loki:
  - [ ] promtail o driver para enviar logs
  - [ ] queries guardadas para debugging
- [ ] Alertas (opcional):
  - [ ] reglas simples: alta tasa de 5xx, dependencia caída

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

## Fase 14 — Documentación y scripts operativos

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

## Fase 15 — Performance tuning (local)

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
