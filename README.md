# Plataforma RAG Local (WSL2 + Docker Compose)

Repositorio para una **plataforma RAG (Retrieval Augmented Generation) 100% local** orientada a usuarios hispanohablantes. Permite **subir documentos**, **extraer texto**, **generar embeddings localmente**, **almacenarlos en un vector DB**, y **chatear con un LLM local** (Ollama + Qwen 2.5 7B Instruct) con **citas y fuentes**.

> Nota: La documentación es deliberadamente detallada para facilitar un desarrollo “production-grade” en un entorno local. El objetivo es que cualquier explicación/respuesta generada por la IA dentro del producto final esté **en español**.

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
  - **Citas/fuentes** por chunk y documento
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

Detalles completos en `docs/architecture.md` y `docs/rag-flow.md`.

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

1) Preparar WSL2 + Ubuntu 22.04 + Docker Desktop (ver `docs/deployment.md`).
2) Clonar repositorio en el filesystem de WSL o en una ruta accesible (cuidando performance).
3) Crear `.env` a partir de `docs/env-example.md`.
4) Ejecutar Docker Compose.
5) Verificar:
   - Frontend: `http://localhost/` (o el host/puerto definido por Traefik)
   - Backend: `http://localhost/api/health`
   - Qdrant: `http://localhost/qdrant` (si se expone)
   - Grafana/Prometheus: `http://localhost/grafana` (si se expone)

> Los pasos exactos (WSL2 + Docker + verificación) están en `docs/deployment.md`.

---

## Variables de entorno

- El ejemplo completo (con comentarios y explicación) está en `docs/env-example.md`.
- Recomendación: **no** subir `.env` al repo.

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

> Este repositorio incluye únicamente documentación y planificación. Las carpetas de código (`frontend/`, `backend/`, etc.) se usarán para implementar el proyecto según `docs/todo.md`.

---

## Roadmap

- Ver `docs/features-roadmap.md` para fases y prioridades.
- Ver `docs/todo.md` para un desglose extremadamente detallado por feature branch.

---

## Notas de seguridad (resumen)

- **Uploads**: validación MIME/size, escaneo antivirus (ClamAV), cuarentena, nombres aleatorios, no ejecución, y políticas estrictas de lectura.
- **WAF**: ModSecurity + OWASP CRS delante del backend.
- **Rate limiting**: por IP + por usuario.
- **Prompt injection**: reglas de “system prompt” y validación/filtrado de contexto recuperado.
- **JWT**: expiración corta para access, refresh rotatorio, revocación.

Detalles completos en `docs/security.md`.

---

## Documentación del proyecto

La documentación vive en `docs/`:

- `docs/technologies.md`
- `docs/architecture.md`
- `docs/deployment.md`
- `docs/api-spec.md`
- `docs/database-schema.md`
- `docs/rag-flow.md`
- `docs/security.md`
- `docs/env-example.md`
- `docs/github-workflow.md`
- `docs/features-roadmap.md`
- `docs/troubleshooting.md`
- `docs/todo.md`

