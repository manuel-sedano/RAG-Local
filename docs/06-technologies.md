# Tecnologías (Stack) y propósito

**Alcance:** stack por categoría. Despliegue **local**, orquestación con **Docker Compose** en **WSL2**.

**Criterios de selección:** componentes **open-source**, **gratuitos**, **local-first**, sin dependencia de servicios cloud gestionados.

---

## Frontend

| Tecnología | Propósito | Explicación corta |
|---|---|---|
| Next.js | Aplicación web y routing | Framework React con SSR/SSG; útil para UI moderna y rendimiento. |
| React | UI declarativa | Componentización, estado y composición para una UX fluida. |
| Tailwind CSS | Estilos utilitarios | Permite un diseño consistente, rápido y mantenible. |
| shadcn/ui | Componentes UI | Componentes accesibles sobre Radix UI, altamente personalizables. |
| Axios | Cliente HTTP | Manejo consistente de requests, interceptors, errores y auth headers. |
| Socket.IO (client) | Streaming y eventos | Canal bidireccional para streaming de tokens y progreso de ingesta. |
| react-markdown | Render de Markdown | Renderiza respuestas del modelo (con sanitización) y formato rico. |
| PDF.js (`pdfjs-dist` o envoltorio React) | Visor PDF en el navegador | Permite abrir el PDF servido por la API con **salto a página N** coherente con las citas RAG; complementa el endpoint `GET .../documents/{id}/file`. |

---

## Backend (API y servicios)

| Tecnología | Propósito | Explicación corta |
|---|---|---|
| FastAPI | API HTTP | Framework Python moderno con tipado, docs OpenAPI y alto rendimiento. |
| Uvicorn | ASGI server | Servidor ASGI para ejecutar FastAPI con buenas prestaciones. |
| Pydantic | Validación/serialización | Modelos de request/response, validación de datos y configuración. |
| SQLAlchemy | ORM | Mapeo relacional para PostgreSQL; transacciones y consultas robustas. |
| Alembic | Migraciones DB | Versionado del esquema PostgreSQL, reproducible y auditable. |
| Socket.IO (server) | Streaming chat | Stream de tokens y eventos de ingesta/progreso hacia el frontend. |

---

## Asincronía / Colas / Background jobs

| Tecnología | Propósito | Explicación corta |
|---|---|---|
| Celery | Orquestación de tareas | Pipeline asíncrono: parse, OCR, chunking, embeddings, upsert. |
| Redis | Broker y cache | Broker para Celery, rate-limit store, caches de sesión/tokens. |

---

## LLM y ejecución local

| Tecnología | Propósito | Explicación corta |
|---|---|---|
| Ollama | Runtime de LLM local | Gestión y ejecución de modelos locales vía API. |
| Qwen 2.5 7B Instruct | Modelo chat | Modelo instruct adecuado para QA y conversación; responder en español. |

---

## Embeddings

| Tecnología | Propósito | Explicación corta |
|---|---|---|
| Sentence Transformers | Generación embeddings | Wrapper para modelos embedding, batching, y normalización. |
| bge-m3 | Embedding model | Modelo multi-lingüe/robusto (incluye español) para RAG. |

---

## RAG (recuperación y orquestación)

| Tecnología | Propósito | Explicación corta |
|---|---|---|
| LlamaIndex | Indexing y retrieval | Componentes para ingestión, índices, retrievers, y trazabilidad. |
| LangChain | Orquestación LLM | Enrutamiento de prompts, cadenas, herramientas y guardrails. |
| FlashRank | Reranking | Reordena candidatos recuperados para mejorar precisión. |
| BM25 | Búsqueda léxica | Complementa embeddings para consultas exactas y nombres propios. |

---

## Procesamiento de documentos

| Tecnología | Propósito | Explicación corta |
|---|---|---|
| PyMuPDF | PDF parsing | Extracción rápida de texto/metadata, páginas y layout básico. |
| python-docx | DOCX parsing | Extracción de contenido de Word conservando estructura simple. |
| Apache Tika | Parsing universal | Extracción de texto/metadata de múltiples formatos (si se habilita). |
| Unstructured | Limpieza/segmentación | Particionado semántico, heurísticas de limpieza, y extracción. |
| Tesseract OCR | OCR | Reconocimiento para PDFs escaneados e imágenes embebidas. |

---

## Vector Database

| Tecnología | Propósito | Explicación corta |
|---|---|---|
| Qdrant | Almacenamiento vectorial | Colección global con payload (KB/doc/user) para filtros. |

---

## Base de datos relacional

| Tecnología | Propósito | Explicación corta |
|---|---|---|
| PostgreSQL | Persistencia principal | Usuarios, KB, documentos, chunks (metadata), chats, auditoría. |

---

## Seguridad y borde (edge)

| Tecnología | Propósito | Explicación corta |
|---|---|---|
| Traefik | Reverse proxy | Enrutamiento por host/path, middlewares, headers y rate limits. |
| JWT | Auth stateless | Tokens access/refresh con expiración, rotación y revocación. |
| Fail2ban | Protección brute force | Bloqueo de IPs con patrones (auth, WAF, 401/403 repetidos). |
| ClamAV | Antivirus uploads | Escaneo de archivos antes de persistir/parsear. |
| ModSecurity | WAF | Inspección y bloqueo de requests maliciosas. |
| OWASP CRS | Reglas WAF | Conjunto de reglas estándar para proteger API web. |

---

## Observabilidad

| Tecnología | Propósito | Explicación corta |
|---|---|---|
| Prometheus | Métricas | Scrape de métricas (API/infra) y alertas locales. |
| Grafana | Dashboards | Visualización de métricas y logs con paneles. |
| Loki | Logs | Agregación/consulta de logs; integración natural con Grafana. |

---

## Desarrollo y operación

| Tecnología | Propósito | Explicación corta |
|---|---|---|
| Docker Compose | Orquestación local | Arranque coordinado de servicios, networking y volúmenes. |
| Git + GitHub | Control de versiones | Flujo por ramas/PRs y releases; convención de commits. |
| VS Code + WSL2 | Entorno dev | IDE con extensión WSL; desarrollo nativo Linux sobre Windows. |

---

## Decisiones de diseño (por qué este stack)

- **Local-first realista**: Ollama + Qdrant + Postgres corren bien en una máquina desktop potente sin depender de GPU cloud.
- **Separación de responsabilidades**: API (FastAPI) y worker (Celery) desacoplan UX de pipelines pesados (OCR/embeddings).
- **Vector store con payload**: una colección global con filtros reduce complejidad operativa y facilita multi-KB.
- **Seguridad defensiva**: WAF + antivirus + rate limiting son críticos cuando aceptas uploads y queries arbitrarias.
- **Observabilidad integrada**: logs+métricas desde el inicio evitan “caja negra” durante ingestión y chat.

