# Arquitectura

**Alcance:** componentes, redes, almacenamiento y flujos (upload, embeddings, retrieval, chat) de la plataforma RAG local.

## Principios y restricciones

- **Sin nube**: no se utilizan servicios cloud.
- **Sin Kubernetes/Helm**: solo **Docker Compose**.
- **Local dentro de WSL2**: pensado para Windows 11 + Ubuntu 22.04 en WSL2.
- **Open-source**: todos los servicios propuestos son gratuitos y auto-hospedables.
- **Seguridad por capas**: WAF, rate limiting, antivirus, JWT, y controles de prompt-injection.

---

## Componentes (vista lógica)

### UI Web (`frontend`)

- Next.js + React para:
  - Login y gestión de sesión (JWT).
  - Gestión de Knowledge Bases (KB).
  - Subida de documentos y seguimiento del procesamiento.
  - Experiencia de chat con streaming, historial y citas.
- Comunicación:
  - REST/HTTP hacia `backend` (Axios).
  - WebSocket/Socket.IO hacia `backend` para streaming de chat y eventos.

### API (`backend`)

- FastAPI expone endpoints para:
  - Auth (JWT).
  - CRUD KB.
  - Upload de documentos + estado de ingesta.
  - Consultas RAG y chat.
  - Historial y auditoría.
- Coordina servicios:
  - Envía trabajos a Celery para ingesta y embeddings.
  - Consulta Qdrant para retrieval.
  - Consulta PostgreSQL para metadatos y control de acceso.
  - Invoca Ollama para generación del LLM (chat).

### Worker (`worker`)

- Celery ejecuta pipelines de alto costo:
  - Validación de archivos y preparación.
  - Escaneo antivirus (integración con ClamAV).
  - Parsing/Extracción (PDF/DOCX/TXT).
  - OCR (si aplica).
  - Limpieza y normalización de texto.
  - Chunking.
  - Embeddings (bge-m3).
  - Upsert en Qdrant con payload de metadatos.

### Persistencia relacional (`postgres`)

PostgreSQL almacena:

- Usuarios, roles, credenciales (hash).
- KBs y membresías.
- Documentos (estado, tamaño, hash, ruta).
- Chunks (metadatos, offsets, referencias a Qdrant).
- Chats e historial.
- Auditoría/seguridad (eventos, rate-limit incidents, etc.).

### Vector DB (`qdrant`)

- Una **colección global** (recomendado) que almacena:
  - Vectores de chunks.
  - Payload con metadatos para filtros:
    - `kb_id`, `doc_id`, `user_id/tenant_id`, `mime_type`, `tags`, `created_at`, etc.
- Soporta:
  - Vector search (cosine/inner product).
  - Filtering por payload.

### LLM local (`ollama`)

- Servicio local para inferencia del modelo:
  - Qwen 2.5 7B Instruct (chat).
- El backend controla:
  - “System prompt” para forzar respuestas en español.
  - Formato de salida con citas.
  - Streaming de tokens.

### Cola y cache (`redis`)

- Broker Celery y result backend.
- Almacén para:
  - Rate limiting.
  - Locks de concurrencia (por doc/KB) durante ingesta.
  - Cache temporal de prompts/contexts si aplica (con límites).

### Reverse proxy y seguridad en el borde (`traefik`, `waf`)

Traefik:

- Enrutamiento por rutas:
  - `/` → frontend
  - `/api` → backend
  - `/socket.io` → backend (Socket.IO)
  - `/grafana`, `/prometheus`, `/loki` → observabilidad (opcional)
- Middlewares:
  - Headers de seguridad.
  - Rate limiting.
  - ForwardAuth (opcional) o solo pasar a backend que valida JWT.

WAF (ModSecurity + OWASP CRS):

- Puede correr como contenedor delante de `backend`.
- Bloquea payloads comunes: SQLi, XSS, RCE, etc.

### Antivirus (`clamav`)

- `clamd` para escaneo.
- El worker llama al escáner antes de persistir/procesar un upload.

### Observabilidad (`prometheus`, `grafana`, `loki`)

- Prometheus scrape:
  - métricas del backend (p. ej. `/metrics`).
  - métricas de infra (node/cadvisor si se incluyen).
- Loki centraliza logs de contenedores.
- Grafana dashboards:
  - latencia API
  - throughput embeddings
  - tiempos por etapa (parse/OCR/chunk/embed)
  - errores por tipo

---

## Arquitectura Docker (vista de despliegue)

### Red (Docker network)

Un network bridge dedicado (p. ej. `rag_net`) donde:

- Solo Traefik publica puertos a host (recomendación).
- Servicios internos se comunican por nombre:
  - `backend` → `postgres:5432`, `redis:6379`, `qdrant:6333`, `ollama:11434`
  - `worker` → mismos servicios internos

### Volúmenes (persistencia)

- `postgres_data` (PostgreSQL)
- `qdrant_data` (Qdrant)
- `ollama_models` (cache/modelos)
- `uploads_data` (archivos subidos; idealmente dentro de `uploads/`)
- `grafana_data`, `prometheus_data`, `loki_data` (observabilidad)

### Rutas y exposición

Recomendación:

- Exponer solo Traefik a host:
  - `80` (HTTP local)
  - `443` (opcional TLS local)
- Mantener Postgres/Redis/Qdrant no expuestos (solo red interna).

---

## Flujos principales

## 1) Flujo de subida (Upload flow)

1. Usuario autenticado sube archivo desde `frontend`.
2. `frontend` envía `multipart/form-data` a `backend`:
   - `kb_id`
   - archivo
   - metadata opcional (tags, idioma declarado, etc.)
3. `backend` valida:
   - JWT, permisos en KB.
   - tipo MIME / extensión permitida.
   - tamaño máximo.
   - checksum (hash) para deduplicación.
4. `backend` guarda el archivo en almacenamiento local (volumen):
   - nombre aleatorio (UUID) + path por KB.
   - estado `UPLOADED`.
5. `backend` encola job Celery `ingest_document(doc_id)` y retorna `202 Accepted`.
6. `worker` procesa:
   - escaneo ClamAV.
   - parse/OCR según tipo.
   - normalización.
   - chunking.
   - embeddings (batching).
   - upsert Qdrant + payload.
   - actualiza estados y contadores en Postgres.
7. `frontend` puede consultar estado por polling o por eventos Socket.IO.

## 2) Flujo de embeddings (Embedding flow)

- El worker calcula embeddings por chunk:
  - batch size configurable.
  - normalización (si se usa cosine).
  - guarda:
    - `qdrant_point_id`
    - `chunk_id` y `doc_id`
    - payload con `kb_id`, `user_id`, `source`, `page`, `chunk_index`, etc.

## 3) Flujo de recuperación (Retrieval flow)

1. Usuario envía una query en el chat de una KB.
2. Backend construye una consulta híbrida:
   - vector search en Qdrant filtrando `kb_id`.
   - BM25 (lexical) sobre un índice local/tabla (según implementación) o via LlamaIndex.
3. Mezcla de resultados (p. ej. weighted score / RRF).
4. Reranking con FlashRank sobre top-K candidatos.
5. Recupera contenido textual y metadatos de chunks/doc en Postgres.

## 4) Flujo de chat (Chat flow)

1. Backend arma “prompt seguro”:
   - instrucciones del sistema (responder en español).
   - política anti prompt injection.
   - contexto con citas (fragmentos + metadata).
2. Backend invoca Ollama con streaming.
3. Streaming de tokens al frontend via Socket.IO.
4. Persistencia:
   - mensaje del usuario
   - respuesta final
   - lista de fuentes/citas (`document_id`, `chunk_id`, `score`, `page_start`/`page_end`, más rutas API resueltas: `viewer_path`, `file_path`; forma del objeto en `09-api-spec.md`)
5. **Enlaces a fuentes:** hipervínculos a `viewer_path` con `page` para PDF (**PDF.js**); descarga opcional con `GET .../documents/{id}/file` autenticado. Formatos en `11-rag-flow.md` §7.4.

## 5) Flujo de networking (Networking flow)

- Todo tráfico externo entra por Traefik.
- Rutas típicas:
  - `/` UI
  - `/api/*` API
  - `/socket.io/*` streaming
- WAF puede colocarse:
  - Traefik → WAF → backend
  - (o) Traefik con middleware WAF si se integra.

## 6) Flujo de almacenamiento (Storage flow)

- Archivos binarios (uploads) en volumen local:
  - políticas de acceso: solo worker/backend.
  - **descarga/visualización autorizada** vía `GET /api/kbs/{kb_id}/documents/{doc_id}/file` con JWT y comprobación de membresía en la KB (nunca exponer `storage_path` ni servir el volumen sin control).
- Texto extraído:
  - guardado como artefacto (opcional) para auditoría y reindex.
- Vectores y payload:
  - Qdrant: “source of truth” para retrieval vectorial.
- Metadatos y control de acceso:
  - Postgres: “source of truth” para autorización y auditoría.

---

## Consideraciones de rendimiento (hardware objetivo)

- OCR y embeddings son las etapas más costosas.
- Con 32GB RAM y NVMe:
  - usar batching y límites de concurrencia en Celery.
  - priorizar colas separadas: `ingest`, `embed`, `ocr`.
- RX 7700 XT:
  - Ollama puede usar aceleración según soporte; si no, CPU aún puede ser viable para 7B con latencia moderada.

---

## Consideraciones de seguridad en la arquitectura

- No exponer Postgres/Redis/Qdrant a host.
- Validar y sanear todo input (WAF + validación app).
- Antivirus antes de parsing.
- Minimizar superficie: rutas internas, network privado, y headers estrictos.
- Guardrails RAG: `12-security.md`, `11-rag-flow.md`.

