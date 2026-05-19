# Especificación de API (FastAPI)

Endpoints REST y eventos Socket.IO para la plataforma RAG local. Implementación de referencia: **FastAPI**; contrato publicable como OpenAPI/Swagger.

## Convenciones generales

- **Base path**: `/api`
- **Formato**: JSON (`application/json`) excepto uploads (`multipart/form-data`)
- **Autenticación**: JWT Bearer (`Authorization: Bearer <token>`)
- **Tiempos**: ISO-8601 en UTC (por ejemplo `2026-05-11T18:45:00Z`)
- **IDs**: UUID v4 (recomendado)
- **Paginación**: `limit` + `cursor` (recomendado) o `page` + `page_size` (opcional)
- **Errores**: formato uniforme

---

## Modelo de error estándar

Formato uniforme de respuestas de error:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {
      "any": "object"
    }
  },
  "request_id": "uuid",
  "timestamp": "2026-05-11T18:45:00Z"
}
```

### Códigos de error sugeridos

- `AUTH_INVALID_CREDENTIALS`
- `AUTH_TOKEN_EXPIRED`
- `AUTH_TOKEN_INVALID`
- `AUTH_FORBIDDEN`
- `KB_NOT_FOUND`
- `DOC_NOT_FOUND`
- `UPLOAD_INVALID_TYPE`
- `UPLOAD_TOO_LARGE`
- `UPLOAD_VIRUS_DETECTED`
- `INGESTION_IN_PROGRESS`
- `RAG_CONTEXT_EMPTY`
- `RATE_LIMITED`
- `INTERNAL_ERROR`

---

## Códigos HTTP

- `200 OK`: operación exitosa
- `201 Created`: creación exitosa
- `202 Accepted`: job asíncrono en cola
- `204 No Content`: borrado exitoso sin body
- `400 Bad Request`: input inválido
- `401 Unauthorized`: token faltante/ inválido
- `403 Forbidden`: sin permisos
- `404 Not Found`: recurso no existe
- `409 Conflict`: conflicto (p. ej. doc duplicado)
- `413 Payload Too Large`: archivo excede límite
- `415 Unsupported Media Type`: MIME no permitido
- `422 Unprocessable Entity`: validación Pydantic
- `429 Too Many Requests`: rate limit
- `500 Internal Server Error`: error inesperado
- `503 Service Unavailable`: dependencia caída (Qdrant/Ollama/etc.)

---

## Autenticación

### POST `/api/auth/login`

Login con usuario/contraseña.

**Request**

```json
{
  "email": "user@example.com",
  "password": "string"
}
```

**Response 200**

```json
{
  "access_token": "jwt",
  "refresh_token": "opaque-urlsafe-string",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "role": "user"
  }
}
```

**Errores**

- `401 AUTH_INVALID_CREDENTIALS`
- `429 RATE_LIMITED`

### POST `/api/auth/refresh`

Intercambia refresh token por un nuevo access token (y refresh rotatorio si aplica).

**Request**

```json
{
  "refresh_token": "opaque-urlsafe-string"
}
```

El `refresh_token` es un **token opaco** almacenado en base de datos como hash (rotación en cada refresh).

**Response 200**

```json
{
  "access_token": "jwt",
  "refresh_token": "opaque-urlsafe-string",
  "token_type": "bearer",
  "expires_in": 900
}
```

### POST `/api/auth/logout`

Revoca refresh token actual (y/o todos si `all_devices=true`).

**Headers**

- `Authorization: Bearer <access_token>`

**Request**

```json
{
  "refresh_token": "opaque-urlsafe-string",
  "all_devices": false
}
```

**Response 204** sin contenido.

---

## Health

### GET `/api/health`

Retorna estado del servicio y dependencias.

**Response 200**

```json
{
  "status": "ok",
  "dependencies": {
    "postgres": "ok",
    "redis": "ok",
    "qdrant": "ok",
    "ollama": "ok"
  },
  "version": "0.1.0",
  "request_id": "uuid"
}
```

**Response 503**

```json
{
  "status": "degraded",
  "dependencies": {
    "postgres": "ok",
    "redis": "ok",
    "qdrant": "down",
    "ollama": "ok"
  }
}
```

---

## Knowledge Bases (KB)

### GET `/api/kbs`

Lista KB visibles para el usuario.

**Headers**

- `Authorization: Bearer <token>`

**Response 200**

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Finanzas",
      "description": "Documentos del área financiera",
      "created_at": "2026-05-11T18:45:00Z",
      "updated_at": "2026-05-11T18:45:00Z"
    }
  ]
}
```

### POST `/api/kbs`

Crea KB.

**Request**

```json
{
  "name": "Finanzas",
  "description": "Documentos del área financiera"
}
```

**Response 201**

```json
{
  "id": "uuid",
  "name": "Finanzas",
  "description": "Documentos del área financiera"
}
```

### GET `/api/kbs/{kb_id}`

Detalles de KB.

### PATCH `/api/kbs/{kb_id}`

Actualiza nombre/descripcion.

### DELETE `/api/kbs/{kb_id}`

Elimina KB (soft delete recomendado). Opcional: “revoke access” para multi-tenant.

**Auditoría** (`security_events.kind`): `KB_CREATED`, `KB_UPDATED`, `KB_DELETED` con `details.kb_id` (UUID en string) y campos relevantes (`name`, etc.).

---

## Documentos

### POST `/api/kbs/{kb_id}/documents/upload`

Sube un documento para ingesta asíncrona.

**Headers**

- `Authorization: Bearer <token>`
- `Content-Type: multipart/form-data`

**Form fields**

- `file`: binario
- `tags`: string opcional (CSV o JSON)
- `source`: string opcional (p. ej. “manual interno”)
- `language`: string opcional (p. ej. `es`)

**Response 202**

```json
{
  "document_id": "uuid",
  "status": "UPLOADED",
  "ingestion_job_id": "uuid"
}
```

`ingestion_job_id`: identificador del encargo asíncrono (p. ej. **task id de Celery**); cuando exista una tabla de jobs de ingesta, puede sustituirse por el UUID del registro.

**Errores**

- `413 UPLOAD_TOO_LARGE`
- `415 UPLOAD_INVALID_TYPE`
- `409` si hash duplicado y se decide bloquear duplicados

### GET `/api/kbs/{kb_id}/documents`

Lista documentos de la KB.

**Query params**

- `status`: `UPLOADED|PROCESSING|READY|FAILED|QUARANTINED`
- `limit`, `cursor`
- `tag`, `source`, `mime_type`

**Response 200**

```json
{
  "items": [
    {
      "id": "uuid",
      "kb_id": "uuid",
      "filename_original": "reporte.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 12345,
      "status": "READY",
      "page_count": 10,
      "chunk_count": 84,
      "created_at": "2026-05-11T18:45:00Z"
    }
  ],
  "next_cursor": null
}
```

### GET `/api/kbs/{kb_id}/documents/{doc_id}`

Detalles y metadatos del documento.

### GET `/api/kbs/{kb_id}/documents/{doc_id}/status`

Estado de procesamiento y métricas por etapa.

**Response 200**

```json
{
  "document_id": "uuid",
  "status": "PROCESSING",
  "stages": {
    "antivirus": { "status": "DONE", "duration_ms": 1200 },
    "parse": { "status": "DONE", "duration_ms": 820 },
    "ocr": { "status": "SKIPPED", "duration_ms": 0 },
    "chunk": { "status": "DONE", "duration_ms": 340 },
    "embed": { "status": "RUNNING", "duration_ms": 12000 },
    "qdrant_upsert": { "status": "PENDING", "duration_ms": 0 }
  },
  "error": null
}
```

### DELETE `/api/kbs/{kb_id}/documents/{doc_id}`

Elimina documento (soft delete recomendado) y desencadena eliminación de vectores asociados.

**Response 204**

### GET `/api/kbs/{kb_id}/documents/{doc_id}/file`

Descarga u ofrece en línea el **archivo original** almacenado para el documento (mismo binario que se subió), tras validar membresía en la KB.

**Headers**

- `Authorization: Bearer <token>` (obligatorio)

**Query params (opcionales)**

- `disposition`: `inline` | `attachment` — controla `Content-Disposition` (por defecto `inline` para PDF y tipos visualizables en navegador, `attachment` para forzar descarga si el cliente lo requiere).

**Response 200**

- Cuerpo: stream del archivo.
- `Content-Type`: según `mime_type` del documento.
- `Content-Disposition`: acorde a `disposition`.

**Errores**

- `403` sin permiso en la KB
- `404` documento inexistente o eliminado
- `409` documento en cuarentena / no listo para servir (según política)

**Citas RAG:** `file_path` referencia esta ruta API; las rutas del volumen de almacenamiento no forman parte del contrato con el cliente. Autenticación: mismo JWT que el resto de la API. Apertura sin cabecera `Authorization`: URLs firmadas de corta duración (`12-security.md` §7.3).

---

## Búsqueda (opcional como endpoint separado)

### POST `/api/kbs/{kb_id}/search`

Devuelve candidatos con score y metadatos (útil para depuración).

**Request**

```json
{
  "query": "¿Cuál es la política de viáticos?",
  "top_k": 20,
  "rerank": true,
  "filters": {
    "tags": ["finanzas", "viaticos"],
    "mime_types": ["application/pdf"]
  }
}
```

**Response 200**

```json
{
  "items": [
    {
      "chunk_id": "uuid",
      "doc_id": "uuid",
      "score": 0.8123,
      "page": 3,
      "snippet": "La política de viáticos establece que...",
      "retrieval_score": 0.0412,
      "rerank_score": 0.8123
    }
  ],
  "metrics": {
    "rerank_status": "done",
    "rerank_latency_ms": 42.5,
    "rerank_backend": "flashrank"
  }
}
```

---

## Chat RAG

### Objeto `citation` (mensajes del asistente)

Cada elemento de `citations` describe una fuente recuperada y enlazable:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `document_id` | uuid | FK a `documents.id`. |
| `chunk_id` | uuid | FK a `chunks.id` (trazabilidad y auditoría). |
| `filename_original` | string | Nombre legible para la UI. |
| `mime_type` | string | Tipo MIME del archivo original. |
| `page_start` | int nullable | Primera página del fragmento (1-based cuando aplique). |
| `page_end` | int nullable | Última página; puede coincidir con `page_start`. |
| `score` | number | Relevancia (retriever/reranker). |
| `viewer_path` | string | Ruta **relativa** de la SPA (Next.js) que abre el visor con contexto de KB y documento; incluir `?page=` para PDF. |
| `file_path` | string | Ruta API `GET .../file` para descarga o fetch autenticado. |

`viewer_path` y `file_path` se obtienen en el servidor al persistir o emitir el mensaje; valores enviados por el modelo sin validación quedan fuera de contrato.

### POST `/api/kbs/{kb_id}/chats`

Crea una sesión de chat (con título opcional).

**Request**

```json
{
  "title": "Consulta de viáticos"
}
```

**Response 201**

```json
{
  "chat_id": "uuid",
  "title": "Consulta de viáticos",
  "created_at": "2026-05-11T18:45:00Z"
}
```

### GET `/api/kbs/{kb_id}/chats`

Lista chats por KB.

### GET `/api/kbs/{kb_id}/chats/{chat_id}`

Detalles del chat (metadatos).

### GET `/api/kbs/{kb_id}/chats/{chat_id}/messages`

Historial de mensajes.

**Response 200**

```json
{
  "items": [
    {
      "id": "uuid",
      "role": "user",
      "content": "¿Cuál es la política de viáticos?",
      "created_at": "2026-05-11T18:45:00Z"
    },
    {
      "id": "uuid",
      "role": "assistant",
      "content": "Según el documento ...",
      "citations": [
        {
          "document_id": "uuid",
          "chunk_id": "uuid",
          "filename_original": "manual-finanzas-2026.pdf",
          "mime_type": "application/pdf",
          "page_start": 3,
          "page_end": 3,
          "score": 0.81,
          "viewer_path": "/kbs/00000000-0000-4000-8000-0000000000a1/documents/00000000-0000-4000-8000-0000000000b2?page=3",
          "file_path": "/api/kbs/00000000-0000-4000-8000-0000000000a1/documents/00000000-0000-4000-8000-0000000000b2/file"
        }
      ],
      "created_at": "2026-05-11T18:45:06Z"
    }
  ]
}
```

### POST `/api/kbs/{kb_id}/chats/{chat_id}/messages`

Envía mensaje del usuario e inicia generación. Puede operar en modo:

- **no-stream**: retorna respuesta final.
- **stream**: retorna ack y el streaming ocurre por Socket.IO.

**Request**

```json
{
  "content": "¿Cuál es la política de viáticos?",
  "stream": true,
  "rag": {
    "top_k": 24,
    "rerank_top_k": 10,
    "hybrid": true,
    "filters": {
      "tags": ["finanzas"]
    }
  }
}
```

**Response 202 (stream=true)**

```json
{
  "message_id": "uuid",
  "status": "STREAMING",
  "socket": {
    "namespace": "/chat",
    "room": "chat:uuid"
  }
}
```

**Response 200 (stream=false)**

```json
{
  "message_id": "uuid",
  "role": "assistant",
  "content": "Según la política de viáticos...",
  "citations": [
    {
      "document_id": "uuid",
      "chunk_id": "uuid",
      "filename_original": "manual.pdf",
      "mime_type": "application/pdf",
      "page_start": 3,
      "page_end": 3,
      "score": 0.81,
      "viewer_path": "/kbs/00000000-0000-4000-8000-0000000000a1/documents/00000000-0000-4000-8000-0000000000b2?page=3",
      "file_path": "/api/kbs/00000000-0000-4000-8000-0000000000a1/documents/00000000-0000-4000-8000-0000000000b2/file"
    }
  ],
  "usage": {
    "prompt_tokens": 1234,
    "completion_tokens": 234
  }
}
```

---

## Streaming (Socket.IO)

### Conexión

- URL: `ws(s)://<host>/socket.io`
- Namespace recomendado: `/chat`
- Auth:
  - JWT en query param `token` o en auth payload (según cliente)

### Eventos recomendados

#### `chat:join`

Cliente se une a la room del chat.

Payload:

```json
{ "chat_id": "uuid" }
```

#### `chat:token`

Streaming de tokens.

```json
{
  "chat_id": "uuid",
  "message_id": "uuid",
  "token": "texto parcial"
}
```

#### `chat:citation`

Emite citas detectadas/confirmadas.

```json
{
  "message_id": "uuid",
  "citations": [
    {
      "document_id": "uuid",
      "chunk_id": "uuid",
      "filename_original": "manual.pdf",
      "mime_type": "application/pdf",
      "page_start": 3,
      "page_end": 3,
      "score": 0.81,
      "viewer_path": "/kbs/00000000-0000-4000-8000-0000000000a1/documents/00000000-0000-4000-8000-0000000000b2?page=3",
      "file_path": "/api/kbs/00000000-0000-4000-8000-0000000000a1/documents/00000000-0000-4000-8000-0000000000b2/file"
    }
  ]
}
```

#### `chat:done`

Finaliza respuesta.

```json
{ "message_id": "uuid", "status": "DONE" }
```

#### `ingest:progress`

Progreso de ingesta por documento.

```json
{
  "document_id": "uuid",
  "stage": "embed",
  "percent": 42
}
```

---

## Seguridad y validaciones (API)

- **CORS**: restringido a orígenes locales permitidos.
- **Rate limiting**:
  - por IP en Traefik
  - por usuario/endpoint en backend (Redis)
- **Uploads**:
  - validar MIME real (no solo extensión)
  - límite de tamaño
  - escaneo antivirus
  - cuarentena si sospechoso
- **Autorización**:
  - cada endpoint que use `kb_id` debe validar membresía/permisos.
- **Prompt injection**:
  - contexto recuperado se sanitiza y se etiqueta como “contenido no confiable”
  - reglas de rechazo/extracción en backend

