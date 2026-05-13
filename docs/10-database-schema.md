# Esquema de base de datos (PostgreSQL) y payloads (Qdrant)

**Alcance:** esquema relacional PostgreSQL y payloads/metadata en Qdrant para:

- Multi-Knowledge Base (KB)
- Control de acceso (usuarios/roles/membresías)
- Documentos y pipeline de ingesta
- Chunks y trazabilidad hacia Qdrant
- Chats, mensajes y citas
- Auditoría y eventos de seguridad

El diseño usa **una colección global en Qdrant** con filtros por payload (`kb_id`, `doc_id`, `owner_id`/`tenant_id`, etc.).

---

## Convenciones

- IDs: `uuid` (con `gen_random_uuid()` de `pgcrypto` o `uuid-ossp`)
- Timestamps: `timestamptz` (UTC)
- Soft delete: `deleted_at` nullable
- Hashes: `sha256` en hex

---

## Extensiones recomendadas

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- Alternativa:
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

---

## Entidades principales

## Tabla: `users`

Usuarios del sistema.

| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| email | text UNIQUE | lowercase; índice |
| password_hash | text | argon2/bcrypt |
| role | text | `admin` / `user` (o tabla separada) |
| is_active | boolean | |
| created_at | timestamptz | |
| updated_at | timestamptz | |

## Tabla: `refresh_tokens`

Rotación y revocación de refresh tokens.

| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| user_id | uuid FK(users.id) | |
| token_hash | text UNIQUE | hash del refresh |
| issued_at | timestamptz | |
| expires_at | timestamptz | |
| revoked_at | timestamptz nullable | |
| replaced_by_id | uuid nullable | para rotación |
| user_agent | text nullable | |
| ip_address | text nullable | |

## Tabla: `knowledge_bases`

Knowledge Bases.

| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| name | text | |
| description | text nullable | |
| owner_user_id | uuid FK(users.id) | si single-tenant |
| created_at | timestamptz | |
| updated_at | timestamptz | |
| deleted_at | timestamptz nullable | |

## Tabla: `kb_memberships` (opcional)

Para compartir KB entre usuarios (multiusuario).

| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| kb_id | uuid FK(knowledge_bases.id) | |
| user_id | uuid FK(users.id) | |
| role | text | `owner`/`editor`/`viewer` |
| created_at | timestamptz | |
| UNIQUE(kb_id, user_id) | | |

## Tabla: `documents`

Metadatos del archivo subido.

| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| kb_id | uuid FK(knowledge_bases.id) | índice |
| uploaded_by_user_id | uuid FK(users.id) | |
| filename_original | text | |
| storage_path | text | ruta interna (no expuesta) |
| mime_type | text | |
| size_bytes | bigint | |
| sha256 | text | deduplicación |
| language | text nullable | `es`, `en`, etc. |
| source | text nullable | origen declarado |
| tags | jsonb | lista/objeto |
| status | text | `UPLOADED/PROCESSING/READY/FAILED/QUARANTINED/DELETED` |
| page_count | int nullable | |
| chunk_count | int nullable | |
| error_code | text nullable | |
| error_message | text nullable | |
| created_at | timestamptz | |
| updated_at | timestamptz | |
| deleted_at | timestamptz nullable | |

Índices recomendados:

```sql
CREATE INDEX IF NOT EXISTS idx_documents_kb ON documents(kb_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_sha256 ON documents(sha256);
CREATE INDEX IF NOT EXISTS idx_documents_tags_gin ON documents USING gin(tags);
```

## Tabla: `document_ingestion_runs`

Trazabilidad por corrida (reintentos).

| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| document_id | uuid FK(documents.id) | |
| attempt | int | 1..n |
| status | text | `RUNNING/DONE/FAILED` |
| started_at | timestamptz | |
| finished_at | timestamptz nullable | |
| metrics | jsonb | duraciones, contadores |
| error_code | text nullable | |
| error_message | text nullable | |

## Tabla: `document_artifacts` (opcional)

Archivos intermedios (texto extraído, OCR, etc.) con control de retención.

| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| document_id | uuid FK(documents.id) | |
| kind | text | `extracted_text`, `ocr_text`, `normalized_text` |
| storage_path | text | ruta del artefacto |
| sha256 | text nullable | |
| created_at | timestamptz | |

## Tabla: `chunks`

Chunks persistidos para trazabilidad y citations.

| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| document_id | uuid FK(documents.id) | índice |
| kb_id | uuid FK(knowledge_bases.id) | redundante para queries rápidas |
| chunk_index | int | orden dentro del doc |
| text | text | cuidado con tamaño; alternativa: guardar solo snippet |
| char_start | int nullable | offset en texto completo |
| char_end | int nullable | |
| page_start | int nullable | |
| page_end | int nullable | |
| section | text nullable | encabezado/capítulo |
| metadata | jsonb | |
| qdrant_point_id | text UNIQUE | id del punto en Qdrant |
| embedding_model | text | `bge-m3` |
| created_at | timestamptz | |

Índices recomendados:

```sql
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_kb ON chunks(kb_id);
CREATE INDEX IF NOT EXISTS idx_chunks_metadata_gin ON chunks USING gin(metadata);
```

## Tabla: `chats`

Sesiones de chat por KB.

| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| kb_id | uuid FK(knowledge_bases.id) | |
| created_by_user_id | uuid FK(users.id) | |
| title | text nullable | |
| created_at | timestamptz | |
| updated_at | timestamptz | |
| deleted_at | timestamptz nullable | |

## Tabla: `chat_messages`

Mensajes de usuario y asistente.

| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| chat_id | uuid FK(chats.id) | índice |
| role | text | `user` / `assistant` / `system` |
| content | text | |
| created_at | timestamptz | |
| model | text nullable | `qwen2.5:7b-instruct` |
| rag_config | jsonb nullable | top_k, rerank, filtros |
| usage | jsonb nullable | tokens, latencias |
| safety_flags | jsonb nullable | bloqueos, inyecciones |

## Tabla: `message_citations`

Citas por mensaje del asistente.

| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| message_id | uuid FK(chat_messages.id) | |
| document_id | uuid FK(documents.id) | |
| chunk_id | uuid FK(chunks.id) | |
| score | real | |
| page_start | int nullable | alineado con `chunks.page_start` (1-based cuando aplique, p. ej. PDF) |
| page_end | int nullable | alineado con `chunks.page_end`; puede igualar `page_start` |
| snippet | text nullable | |
| created_at | timestamptz | |

Los campos `viewer_path` y `file_path` de la API **no** se almacenan en esta tabla: se calculan al serializar la respuesta a partir de `document_id`, `kb_id` del chat y `page_start` (contrato en `09-api-spec.md`).

## Tabla: `rate_limit_events` (opcional)

Auditoría de rate limiting.

| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| user_id | uuid nullable | |
| ip_address | text nullable | |
| endpoint | text | |
| method | text | |
| reason | text | |
| created_at | timestamptz | |

## Tabla: `security_events` (opcional)

Auditoría de eventos: virus detectado, WAF block, brute-force, etc.

| Campo | Tipo | Notas |
|---|---|---|
| id | uuid PK | |
| user_id | uuid nullable | |
| ip_address | text nullable | |
| kind | text | `WAF_BLOCK`, `VIRUS_DETECTED`, `LOGIN_FAILED`, ... |
| details | jsonb | |
| created_at | timestamptz | |

---

## Relaciones (diagrama textual)

- `users` 1—N `refresh_tokens`
- `users` 1—N `knowledge_bases` (si owner directo)
- `knowledge_bases` 1—N `documents`
- `documents` 1—N `chunks`
- `knowledge_bases` 1—N `chats`
- `chats` 1—N `chat_messages`
- `chat_messages` 1—N `message_citations` (solo para role assistant)

---

## Ejemplos de metadatos (Postgres)

### `documents.tags` (jsonb)

```json
["finanzas", "viaticos", "politica"]
```

O como objeto:

```json
{
  "tags": ["finanzas", "viaticos"],
  "department": "Finanzas",
  "confidentiality": "internal"
}
```

### `chunks.metadata` (jsonb)

```json
{
  "page_start": 3,
  "page_end": 3,
  "section": "Políticas",
  "source": "manual-finanzas-2026.pdf",
  "ocr": false
}
```

---

## Diseño Qdrant (colección global)

### Nombre de colección

Recomendación:

- `rag_chunks_v1`

### Vector

- Dimensión: depende del modelo embeddings (bge-m3).
- Distancia: `Cosine` (común con embeddings normalizados).

### Payload mínimo recomendado

Campos para filtros y trazabilidad:

- `kb_id`: UUID
- `doc_id`: UUID
- `chunk_id`: UUID
- `owner_user_id`: UUID (o `tenant_id`)
- `mime_type`: string
- `tags`: array<string>
- `language`: string
- `source`: string
- `created_at`: ISO timestamp
- `page_start`, `page_end`: int
- `chunk_index`: int
- `text`: (opcional) snippet corto (evitar full text si crece demasiado)

### Ejemplo de payload (Qdrant)

```json
{
  "kb_id": "6b41f2fd-1a7d-4b0c-8a6c-9a1b6e2d3b10",
  "doc_id": "b9fa1ac1-5a74-48b3-8b3b-5d88c5e2c2a1",
  "chunk_id": "d6d6d3a0-7c1b-4c8f-8a40-2a4f0d3c0b12",
  "owner_user_id": "8e5bd4c6-2d47-4c26-8c53-6e3b23d9a2ab",
  "mime_type": "application/pdf",
  "tags": ["finanzas", "viaticos"],
  "language": "es",
  "source": "manual-finanzas-2026.pdf",
  "created_at": "2026-05-11T18:45:00Z",
  "page_start": 3,
  "page_end": 3,
  "chunk_index": 17,
  "text": "La política de viáticos establece que..."
}
```

### Ejemplo de filtro por KB + tags (Qdrant)

```json
{
  "must": [
    { "key": "kb_id", "match": { "value": "6b41f2fd-1a7d-4b0c-8a6c-9a1b6e2d3b10" } },
    { "key": "tags", "match": { "any": ["viaticos"] } }
  ]
}
```

---

## Estrategia de eliminación / reindexado

- **Soft delete en Postgres**:
  - marcar `documents.deleted_at`
  - marcar `chunks` como obsoletos (opcional)
- **Hard delete en Qdrant**:
  - borrar por filtro `doc_id` (y `kb_id` si se requiere)
- **Reindexado**:
  - nueva colección `rag_chunks_v2` si cambia el modelo de embeddings o chunking
  - migración progresiva: dual-write o backfill con jobs

---

## Checklist de consistencia (recomendado)

- [ ] Cada `chunk` en Postgres tiene `qdrant_point_id` existente.
- [ ] No existen puntos Qdrant sin `chunk_id`/`doc_id`.
- [ ] `documents.chunk_count` coincide con conteo real de `chunks`.
- [ ] En borrado de documento: se eliminan chunks y puntos vectoriales (o se marcan como no activos).

