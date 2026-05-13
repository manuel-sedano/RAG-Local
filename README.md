# Plataforma RAG Local (WSL2 + Docker Compose)

Repositorio para una **plataforma RAG (Retrieval Augmented Generation) 100% local** orientada a usuarios hispanohablantes. Permite **subir documentos**, **extraer texto**, **generar embeddings localmente**, **almacenarlos en un vector DB**, y **chatear con un LLM local** (Ollama + Qwen 2.5 7B Instruct) con **citas y fuentes**.

La documentación del repositorio cubre despliegue y operación con nivel de detalle orientado a producción en entorno local. Las respuestas del producto (chat RAG) se definen en **español**.

---

## Objetivos del proyecto

- **100% local**: sin servicios cloud; todo open-source y gratuito.
- **Docker Compose**: sin Kubernetes/Helm.
- **WSL2**: pensado para Windows 11 con Ubuntu 22.04 en WSL2.
- **RAG robusto**: búsqueda híbrida (vector + BM25), reranking, filtrado por metadatos, defensa contra prompt injection.
- **Seguridad y operación**: reverse proxy, WAF, rate limiting, antivirus, logs, métricas y trazabilidad.

---

## Funcionalidades (feature set)

- **Autenticación**
  - Login con usuario/contraseña
  - **JWT** (access/refresh) y rotación
  - Roles básicos (p. ej. `admin`, `user`)
- **Knowledge Bases (KB)**
  - Múltiples KB por usuario/organización (según diseño)
  - Documentos agrupados por KB
  - Filtros por metadatos (origen, etiquetas, fecha, tipo)
- **Ingesta de documentos**
  - Subida segura (validación, límites, MIME)
  - Soporte: **PDF**, **DOCX**, **TXT**
  - OCR (cuando aplique)
  - Chunking configurable
  - Generación de embeddings local (bge-m3)
  - Indexado en **Qdrant** con payload de metadatos
- **Consulta / Chat**
  - Recuperación vectorial + BM25 (híbrida)
  - Reranking con **FlashRank**
  - Respuesta en streaming (Socket.IO)
  - **Citas/fuentes** por chunk y documento, con **enlaces en la UI** al documento original y a la **página** cuando el formato lo permite (PDF mediante `page_start`/`page_end` en ingesta; flujo en `docs/11-rag-flow.md` §7.4–§9.4)
  - Historial de chat por KB
  - Protección contra prompt injection y data exfiltration
- **Plataforma / Operación**
  - Reverse proxy (Traefik)
  - WAF (ModSecurity + OWASP CRS)
  - Rate limiting
  - Antivirus (ClamAV) para archivos subidos
  - Observabilidad: Prometheus + Grafana + Loki

---

## Stack tecnológico (resumen)

### Frontend

- Next.js + React
- Tailwind CSS + shadcn/ui
- Axios
- Socket.IO
- react-markdown
- PDF.js (visor PDF en el cliente; citas con salto a página)

### Backend

- FastAPI + Uvicorn
- SQLAlchemy + Alembic
- Pydantic
- Celery + Redis (colas, pipeline asíncrono)

### RAG / IA local

- Ollama
- Modelo: Qwen 2.5 7B Instruct
- Embeddings: Sentence Transformers (bge-m3)
- RAG: LlamaIndex + LangChain (orquestación), FlashRank (rerank), BM25 (lexical)

### Datos

- PostgreSQL (metadatos, usuarios, KB, documentos, chats)
- Qdrant (vectores + payload con metadatos)

### Seguridad / Networking

- Traefik
- Fail2ban
- ClamAV
- ModSecurity + OWASP CRS
- JWT

### Observabilidad

- Prometheus
- Grafana
- Loki

---

## Arquitectura (resumen)

**Componentes principales (Docker Compose):**

- `frontend`: UI web (Next.js) expuesta a través de Traefik.
- `backend`: API (FastAPI) + Socket.IO para streaming.
- `worker`: Celery para ingesta/embeddings/indexado.
- `postgres`: metadatos y persistencia relacional.
- `redis`: broker y backend de resultados Celery.
- `qdrant`: vector DB único con payload por metadatos (filtros por KB/documento/usuario).
- `ollama`: LLM local para chat y/o tareas auxiliares.
- `traefik`: reverse proxy + TLS local opcional + middlewares de seguridad.
- `waf` (si se despliega separado): ModSecurity + CRS protegiendo rutas expuestas.
- `clamav`: daemon para escaneo de archivos.
- `prometheus`, `grafana`, `loki`: observabilidad.

Flujos clave:

- **Upload → Parse → Chunk → Embed → Upsert Qdrant**
- **Query → Hybrid retrieval → Rerank → Prompt safe → LLM streaming**

Ampliación: `docs/05-architecture.md`, `docs/11-rag-flow.md`.

---

## Requisitos

### Hardware objetivo (referencia)

- AMD Ryzen 7 5700X
- AMD RX 7700 XT 12GB
- 32GB RAM
- 1TB NVMe

### Software

- Windows 11
- WSL2 con Ubuntu 22.04
- Docker Desktop con integración WSL2
- Git

---

## Instalación y arranque (alto nivel)

1) Preparar WSL2 + Ubuntu 22.04 + Docker Desktop (`docs/01-deployment.md`).
2) Clonar repositorio en el filesystem de WSL o en una ruta accesible (cuidando performance).
3) Crear `.env` a partir de `docs/04-env-example.md`.
4) Ejecutar Docker Compose.
5) Verificar:
   - Frontend: `http://localhost/` (o el host/puerto definido por Traefik)
   - Backend: `http://localhost/api/health`
   - Qdrant: `http://localhost/qdrant` (si se expone)
   - Grafana/Prometheus: `http://localhost/grafana` (si se expone)

Procedimiento detallado: `docs/01-deployment.md`.

---

## Variables de entorno

- Plantilla comentada: `docs/04-env-example.md`.
- El archivo `.env` permanece fuera del control de versiones.

---

## Estructura del repositorio

Estructura objetivo (GitHub-ready):

```text
project/
├── frontend/
├── backend/
├── docker/
├── uploads/
├── docs/
├── scripts/
├── .env
├── docker-compose.yml
├── .gitignore
└── README.md
```

**Estado del repositorio:** `docker-compose` con placeholders; **frontend** Next.js 16 (App Router, Tailwind, shadcn/ui, ESLint); **backend** layout `app/` + `pyproject.toml` (Ruff, Black, isort, pytest). Siguientes fases en `docs/08-todo.md`.

---

## Roadmap

- Ver `docs/07-features-roadmap.md` para fases y prioridades.
- Ver `docs/08-todo.md` para un desglose extremadamente detallado por feature branch.

---

## Notas de seguridad (resumen)

- **Uploads**: validación MIME/size, escaneo antivirus (ClamAV), cuarentena, nombres aleatorios, no ejecución, y políticas estrictas de lectura.
- **WAF**: ModSecurity + OWASP CRS delante del backend.
- **Rate limiting**: por IP + por usuario.
- **Prompt injection**: reglas de “system prompt” y validación/filtrado de contexto recuperado.
- **JWT**: expiración corta para access, refresh rotatorio, revocación.

Detalles completos en `docs/12-security.md`.

---

## Documentación del proyecto

La documentación vive en `docs/`. **Empieza por** `docs/README.md` (orden de lectura) y luego:

- `docs/01-deployment.md`
- `docs/02-smoke-test.md`
- `docs/03-github-workflow.md`
- `docs/04-env-example.md`
- `docs/05-architecture.md`
- `docs/06-technologies.md`
- `docs/07-features-roadmap.md`
- `docs/08-todo.md`
- `docs/09-api-spec.md`
- `docs/10-database-schema.md`
- `docs/11-rag-flow.md`
- `docs/12-security.md`
- `docs/13-troubleshooting.md`
- `docs/14-comercializacion-mvp-precios.md`

