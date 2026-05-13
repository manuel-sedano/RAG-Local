# Roadmap de funcionalidades (MVP → fases futuras)

**Alcance:** construcción incremental de una plataforma RAG local, segura y operable, en fases con objetivos, entregables y criterios de “done”.

Desglose por tareas: `08-todo.md`.

---

## Definiciones

- **MVP**: mínimo producto viable con RAG funcional end-to-end, auth básica, uploads, búsqueda y chat con citas.
- **Hardening**: seguridad/observabilidad/performance necesarios para uso real.
- **Escalabilidad local**: mejoras de calidad, DX, y robustez sin nube.

---

## Fase 0 — Bootstrap del repositorio (Semana 1)

**Objetivo**: dejar el repo listo para desarrollo, con Docker Compose, estructura, y documentación base.

**Entregables**

- Estructura `frontend/`, `backend/`, `docker/`, `scripts/`, `uploads/`, `docs/`
- `docker-compose.yml` inicial (servicios base)
- `.env` ejemplo documentado
- Linting y formato base para backend/frontend

**Criterios Done**

- `docker compose up -d` levanta servicios core sin errores
- `GET /api/health` responde (aunque sea “stub”)
- Frontend carga una pantalla base

---

## Fase 1 — MVP RAG end-to-end (Semanas 2–4)

**Objetivo**: permitir subir documentos, indexarlos, y chatear con citas dentro de una KB.

### MVP-1: Auth + KB + Uploads

- Auth:
  - login JWT access/refresh
  - RBAC mínimo
- KB:
  - CRUD KB
  - permisos básicos (owner)
- Uploads:
  - PDF/DOCX/TXT
  - validación MIME/size
  - pipeline asíncrono (Celery)

### MVP-2: Ingesta y embeddings

- Parsing:
  - PDF (PyMuPDF), DOCX (python-docx), TXT
- Chunking:
  - ventana deslizante con overlap
- Embeddings:
  - bge-m3
- Vector store:
  - Qdrant colección global + payload

### MVP-3: Retrieval + Chat con streaming

- Retrieval:
  - vector search con filtros por `kb_id`
  - BM25 básico (aunque sea simple al inicio)
  - reranking FlashRank
- Chat:
  - streaming tokens Socket.IO
  - guardado de historial
  - citas (mapeadas por backend, no “inventadas” por el LLM)
  - **enlaces en UI** al documento original y salto a **página** cuando exista metadata de página (PDF; DOCX/TXT según límites en `docs/11-rag-flow.md`)

**Criterios Done (MVP)**

- Usuario crea KB, sube doc, espera ingesta, pregunta y obtiene respuesta en español con fuentes
- Documentos se filtran por KB
- Pipeline asíncrono muestra estado

---

## Fase 2 — Hardening de seguridad (Semanas 5–6)

**Objetivo**: reducir riesgos reales de uploads y abuso.

Prioridades:

- Antivirus:
  - ClamAV integrado al pipeline
- WAF:
  - ModSecurity + OWASP CRS en modo observación → bloqueo
- Rate limiting:
  - Traefik + Redis en backend
- Prompt injection defenses:
  - sanitización de contexto
  - grounding enforcement
- Auditoría:
  - security events en DB
  - logs estructurados con request_id

**Criterios Done**

- Uploads maliciosos se cuarentenan
- Brute-force y spam se limitan sin romper UX normal
- Prompt injection típica es mitigada

---

## Fase 3 — Observabilidad y operación local (Semanas 7–8)

**Objetivo**: hacer visible el sistema y facilitar troubleshooting.

Entregables:

- Prometheus scrape del backend
- Grafana dashboards (ingesta, chat, errores)
- Loki para logs centralizados
- Alertas locales básicas (opcional)

**Criterios Done**

- Puedes diagnosticar cuellos de botella (OCR vs embed vs qdrant)
- Errores quedan correlacionados por request_id / document_id

---

## Fase 4 — Calidad RAG y experiencia de usuario (Semanas 9–10)

**Objetivo**: mejorar relevancia y UX.

Entregables:

- Mejoras de chunking (semántico por secciones cuando posible)
- Mejoras de hybrid search:
  - RRF / weighting ajustable
  - UI para filtros (tags/source/date)
- Prompting:
  - formatos de respuesta (resumen, paso a paso, bullet points)
  - modo “citar siempre”/“estricto”
- UI:
  - vista de documentos con previews
  - vista de citas resaltadas
  - búsqueda por documento

---

## Fase 5 — Capacidades avanzadas (futuro)

Ideas (priorizar según uso real):

- Multiusuario real con roles por KB (`viewer/editor/owner`)
- Versionado de documentos / reindex incremental
- “Collections v2” (reindex con nuevos embeddings)
- Evaluación offline:
  - dataset de queries
  - métricas (MRR/nDCG proxy) y regressions
- Herramientas:
  - export/import de KB
  - backup/restore con scripts
- Integraciones locales:
  - directorios watch para ingesta automática
  - conectores (filesystem, git repos)

