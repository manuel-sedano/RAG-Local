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

- [ ] Revisar y alinear `README.md` y `docs/*.md` con la estructura final del repo
- [ ] Crear plantilla de PR (si se decide) y convención de issues (opcional)
- [ ] Definir estándares de respuesta del asistente (siempre en español) en un doc de producto (opcional)

---

## Fase 1 — Fundaciones backend (DB, config, health, base API)

### Feature branch: `feat/backend-core`

- [ ] Configuración:
  - [ ] implementar loader de `.env` (pydantic settings)
  - [ ] separar settings por ambiente (`local`, `test`)
  - [ ] validar settings al boot (fallar rápido)
- [ ] Logging:
  - [ ] logging estructurado (JSON o key-value) con `request_id`
  - [ ] middleware de `request_id` (propagar en logs/responses)
  - [ ] sanitizar logs (no tokens, no passwords)
- [ ] Health:
  - [ ] endpoint `GET /api/health`
  - [ ] chequeo de Postgres, Redis, Qdrant, Ollama
  - [ ] retornar `503` si dependencia crítica cae
- [ ] Seguridad base:
  - [ ] headers de seguridad (via Traefik y/o FastAPI)
  - [ ] CORS restringido por `CORS_ALLOW_ORIGINS`

### Feature branch: `feat/db-schema-alembic`

- [ ] DB:
  - [ ] definir modelos SQLAlchemy para tablas core:
    - [ ] `users`
    - [ ] `refresh_tokens`
    - [ ] `knowledge_bases`
    - [ ] `kb_memberships` (si multiusuario)
    - [ ] `documents`
    - [ ] `document_ingestion_runs`
    - [ ] `chunks`
    - [ ] `chats`
    - [ ] `chat_messages`
    - [ ] `message_citations`
    - [ ] `security_events` (opcional)
    - [ ] `rate_limit_events` (opcional)
  - [ ] crear migraciones Alembic iniciales
  - [ ] crear índices recomendados (GIN/BTREE)
- [ ] Testing:
  - [ ] fixture de DB test (Postgres en Docker o sqlite compatible si viable)
  - [ ] test de migración (alembic upgrade head)

---

## Fase 2 — Autenticación y autorización

## Feature: auth (JWT)

### Feature branch: `feat/auth-jwt`

- [ ] Backend:
  - [ ] modelo `User` + validaciones (email único, is_active)
  - [ ] hashing de passwords (Argon2id o bcrypt con costo alto)
  - [ ] servicio JWT:
    - [ ] emitir access token con TTL corto
    - [ ] emitir refresh token con TTL largo
    - [ ] incluir `jti` en access
  - [ ] refresh token store:
    - [ ] persistir hash de refresh en DB
    - [ ] rotación de refresh (invalidate old, create new)
    - [ ] revocación por logout
  - [ ] endpoints:
    - [ ] `POST /api/auth/login`
    - [ ] `POST /api/auth/refresh`
    - [ ] `POST /api/auth/logout`
  - [ ] dependencias FastAPI:
    - [ ] `get_current_user` (bearer)
    - [ ] `require_role` / `require_kb_access`
  - [ ] rate limit:
    - [ ] login rate limit por IP + email
    - [ ] lockout progresivo por usuario
  - [ ] auditoría:
    - [ ] registrar `LOGIN_FAILED`, `LOGIN_SUCCESS`, `TOKEN_REFRESH`, `LOGOUT`
- [ ] Frontend:
  - [ ] UI login (shadcn/ui)
  - [ ] estado de sesión (access/refresh)
  - [ ] interceptor Axios para `401` → refresh → retry
  - [ ] logout
  - [ ] manejo de expiración y mensajes al usuario en español
- [ ] Testing:
  - [ ] unit tests hashing/JWT
  - [ ] integration tests login/refresh/logout
  - [ ] tests de lockout/rate limit (básicos)
- [ ] Docs:
  - [ ] confirmar que `docs/09-api-spec.md` coincide con implementación real

---

## Fase 3 — Knowledge Bases (KB)

## Feature: knowledge bases

### Feature branch: `feat/kb-crud`

- [ ] Backend:
  - [ ] modelo `KnowledgeBase`
  - [ ] (si multiusuario) modelo `kb_memberships` y roles por KB
  - [ ] endpoints:
    - [ ] `GET /api/kbs`
    - [ ] `POST /api/kbs`
    - [ ] `GET /api/kbs/{kb_id}`
    - [ ] `PATCH /api/kbs/{kb_id}`
    - [ ] `DELETE /api/kbs/{kb_id}` (soft delete)
  - [ ] autorización:
    - [ ] validar acceso por KB en cada endpoint
  - [ ] eventos/auditoría:
    - [ ] `KB_CREATED`, `KB_UPDATED`, `KB_DELETED`
- [ ] Frontend:
  - [ ] vista lista KB
  - [ ] crear/editar/eliminar KB
  - [ ] selector de KB activo
  - [ ] estados vacíos y errores claros (en español)
- [ ] Testing:
  - [ ] tests CRUD KB
  - [ ] tests autorización (no acceder KB ajena)

---

## Fase 4 — Uploads y pipeline de ingesta (async)

## Feature: uploads + ingestion

### Feature branch: `feat/uploads-api`

- [ ] Backend:
  - [ ] endpoint upload:
    - [ ] `POST /api/kbs/{kb_id}/documents/upload`
    - [ ] validación `kb_id` + permisos
    - [ ] validación de MIME (allowlist)
    - [ ] validación magic bytes (preferido)
    - [ ] límite tamaño (MB)
    - [ ] calcular `sha256` para deduplicación
    - [ ] storage seguro:
      - [ ] generar nombre UUID
      - [ ] evitar path traversal
      - [ ] guardar fuera del web root
  - [ ] endpoints docs:
    - [ ] `GET /api/kbs/{kb_id}/documents`
    - [ ] `GET /api/kbs/{kb_id}/documents/{doc_id}`
    - [ ] `GET /api/kbs/{kb_id}/documents/{doc_id}/status`
    - [ ] `GET /api/kbs/{kb_id}/documents/{doc_id}/file` (stream autenticado; `Content-Disposition` inline/attachment)
    - [ ] `DELETE /api/kbs/{kb_id}/documents/{doc_id}`
  - [ ] modelo `Document` con estados:
    - [ ] `UPLOADED`, `PROCESSING`, `READY`, `FAILED`, `QUARANTINED`, `DELETED`
  - [ ] encolar job Celery al upload:
    - [ ] `ingest_document(document_id)`
- [ ] Frontend:
  - [ ] componente upload (drag&drop)
  - [ ] validación client-side (tamaño/tipo) como UX, no seguridad
  - [ ] progreso:
    - [ ] mostrar documentos y estatus
    - [ ] polling o socket para status updates
  - [ ] metadatos:
    - [ ] tags
    - [ ] source
    - [ ] language
- [ ] Docker:
  - [ ] volumen `uploads` persistente
  - [ ] permisos y ownership (WSL)
- [ ] Testing:
  - [ ] tests upload OK (pdf/docx/txt)
  - [ ] tests upload invalid mime
  - [ ] tests upload oversized
  - [ ] tests delete doc (soft delete)

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
