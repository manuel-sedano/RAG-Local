# Flujo RAG (chunking → embeddings → retrieval → reranking → prompting)

**Alcance:** flujo RAG en despliegue local con chunking configurable, embeddings (bge-m3), búsqueda híbrida (vector + BM25), reranking (FlashRank), prompting, filtrado por metadatos y mitigación de prompt injection.

**Salida:** respuestas **en español**, con **citas** y **trazabilidad** a fragmentos y documentos.

---

## 1) Ingesta: parsing y normalización

### 1.1 Tipos soportados

- PDF (`application/pdf`)
- DOCX (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`)
- TXT (`text/plain`)

### 1.2 Extracción por tipo

- **PDF**
  - Primario: PyMuPDF para extraer texto por página.
  - Fallback: Apache Tika / Unstructured si PyMuPDF falla o el layout es complejo.
  - Si el PDF está escaneado o tiene poco texto:
    - OCR (Tesseract) por página/imagen.
- **DOCX**
  - python-docx para texto y estructura básica (títulos, párrafos).
  - Unstructured para segmentación si el documento es irregular.
- **TXT**
  - Lectura directa con detección de encoding (UTF-8, Latin-1, etc.).

### 1.3 Limpieza y normalización

Objetivos:

- Reducir ruido (headers/footers repetidos).
- Normalizar espacios, saltos de línea, guiones de final de línea.
- Preservar estructura útil (títulos, listas) cuando aporte a recuperación.

Reglas típicas:

- Eliminar líneas repetidas en muchas páginas (heurística).
- Unir palabras cortadas por guiones por salto de línea.
- Normalizar múltiplos de whitespace.

Artefactos opcionales:

- Guardar `extracted_text` y `normalized_text` para reindexado sin reparsear binarios.

---

## 2) Chunking (segmentación)

### 2.1 Principios

Chunking debe balancear:

- **Recall** (encontrar el fragmento correcto)
- **Precision** (no meter contexto irrelevante)
- **Costo** (embeddings y tokens)
- **Citas** (página/sección)

### 2.2 Estrategias de chunking recomendadas

En orden de preferencia:

1. **Chunking semántico por secciones** (si se detectan encabezados).
2. **Chunking por párrafos** con límite de tokens.
3. **Chunking por ventana deslizante** (sliding window) con overlap.

Parámetros recomendados (MVP, ajustables):

- `chunk_size_tokens`: 350–600 (según densidad)
- `chunk_overlap_tokens`: 60–120
- `max_chunk_size_tokens`: 800 (hard cap)

Metadatos por chunk:

- `page_start`, `page_end`
- `chunk_index`
- `section` (si aplica)
- `ocr`: boolean
- `source`: filename

### 2.3 Anti-fragmentación de conceptos

Reglas:

- Nunca cortar dentro de tablas/listas largas sin re-empaquetar.
- Mantener encabezado + párrafo siguiente juntos cuando sea corto.
- Si el chunk es demasiado pequeño (< 50 tokens), unirlo con vecino.

---

## 3) Embeddings (bge-m3)

### 3.1 Pipeline

1. Recibir lista de chunks ya normalizados.
2. Ejecutar embeddings en batches:
   - `batch_size` dinámico según RAM.
3. Normalizar vector si se usa Cosine.
4. Upsert en Qdrant con payload completo.

### 3.2 Consideraciones de idioma

- `bge-m3` es adecuado para español; aun así:
  - guardar `language` (detectado o declarado) en metadata.
  - filtrar por idioma en retrieval si el caso lo requiere.

### 3.3 Versionado

Guardar en Postgres:

- `embedding_model`: `bge-m3`
- `embedding_model_revision` (si aplica)
- `chunking_config_hash` para trazabilidad

Esto permite:

- reindexar cuando cambie chunking o embeddings
- convivir con `rag_chunks_v2` en Qdrant

---

## 4) Almacenamiento en Qdrant (vector + payload)

### 4.1 Colección global

Una sola colección (p. ej. `rag_chunks_v1`) con payload para filtrar.

Ventajas:

- Simplifica operación (1 colección).
- Filtros por `kb_id`/`doc_id`.
- Facilita multi-KB sin crear colecciones por KB.

### 4.2 Payload esencial

Debe incluir:

- `kb_id`, `doc_id`, `chunk_id`
- `tags`, `source`, `mime_type`, `language`
- `page_start`, `page_end`
- `chunk_index`
- opcional: `text` como snippet corto

---

## 5) Retrieval (búsqueda híbrida)

### 5.1 Motivación

Solo vector search puede fallar cuando:

- hay siglas/nombres propios (p. ej. “NOM-035”)
- hay términos exactos
- hay queries muy cortas

BM25 complementa con match léxico.

### 5.2 Pasos (híbrido)

1. Validar query:
   - longitud mínima
   - limpiar caracteres raros
2. Construir filtros:
   - `kb_id` obligatorio
   - tags/source/mime_type opcionales
3. Recuperación vectorial (Qdrant):
   - topK vector: 50 (ejemplo)
4. Recuperación BM25:
   - índice local por KB o por doc (según implementación)
   - topK bm25: 50
5. Combinar resultados:
   - RRF (Reciprocal Rank Fusion) o weighted sum
6. Seleccionar top candidates (ej. 30) para rerank.

### 5.3 Metadata filtering

Ejemplos de filtros útiles:

- `tags` contiene cualquiera / todos
- `source` exacto
- rango de fechas (si payload guarda `created_at`)
- `mime_type` en lista

Regla:

- **Nunca** permitir que el cliente envíe filtros que rompan control de acceso:
  - `kb_id` debe forzarse server-side
  - si multi-tenant, forzar `tenant_id`

---

## 6) Reranking (FlashRank)

### 6.1 Qué mejora

Reranking reordena candidatos usando un modelo ligero que considera:

- query completa
- fragmento completo
- relevancia textual fina

### 6.2 Proceso

1. Tomar top-N (ej. 30) del híbrido.
2. Rerank a top-M (ej. 8–12).
3. Solo esos top-M entran como contexto al prompt del LLM.

### 6.3 Límites

- Rerank acotado a decenas de candidatos por coste de latencia.
- Medir latencia y ajustar N/M.

---

## 7) Construcción del prompt (prompting)

### 7.1 Objetivos del prompt

- Responder **en español** siempre.
- Usar el contexto recuperado solo como “fuentes”.
- No inventar (no alucinación): si no hay evidencia, decirlo.
- Incluir citas por afirmación relevante.
- Mantener tono profesional.

### 7.2 Plantilla de alto nivel (conceptual)

Componentes:

- **System**:
  - rol, idioma, políticas, seguridad
- **Developer/Policy** (si se usa):
  - formato de salida (citas)
  - cómo manejar incertidumbre
- **Context**:
  - lista de chunks con metadatos
  - advertencia: “contenido no confiable”
- **User**:
  - pregunta

### 7.3 Formato de citas

Recomendación de salida:

- Respuesta en texto natural.
- Sección “Fuentes” con:
  - documento
  - página (o rango, si el chunk cruza páginas)
  - identificador de chunk (para auditoría)

Ejemplo de respuesta deseada (en español):

> Según el documento de políticas de viáticos, los reembolsos requieren comprobantes válidos y autorización previa del supervisor.  
>
> **Fuentes:**  
> - Manual Finanzas 2026, pág. 3 (chunk 17)  
> - Manual Finanzas 2026, pág. 4 (chunk 22)

### 7.4 Enlaces a documento y página (UI y API)

Los enlaces por cita se apoyan en: metadatos de ingesta (`document_id`, `page_start` / `page_end` en `chunks`, `10-database-schema.md`), transmisión del binario por HTTP autenticado (`09-api-spec.md`, `GET .../documents/{id}/file`) y ruta de aplicación que inicializa el visor en la página indicada. Operación posible sin object storage externo.

| Formato | Enlace a documento | Enlace / salto a página | Notas |
|---------|-------------------|-------------------------|--------|
| **PDF** | Sí (descarga o visor in-app) | Sí, de forma fiable | Extractores tipo PyMuPDF aportan índice de página por chunk; **PDF.js** posiciona la vista en la página N. |
| **DOCX** | Sí (descarga o vista texto) | Parcial / aproximada | El número de página depende del motor de composición; sin PDF intermedio, la correlación chunk↔página es imprecisa. Conversión a PDF en ingesta unifica el salto por página. |
| **TXT** | Sí | No aplica | Metadatos opcionales: offset o número de línea; no hay noción de página. |

**Comportamiento**

1. **Citas:** el backend arma la lista desde los chunks incluidos en el contexto; las URLs del payload no se aceptan sin validación desde la salida del modelo.
2. **Payload hacia el cliente:** además de `document_id`, `chunk_id`, `score` y rango de página, se envían rutas relativas para hipervínculos:
   - `viewer_path`: ruta de aplicación (p. ej. `/kbs/{kb_id}/documents/{document_id}?page=3`); acceso tras autenticación, sin URL anónima al volumen.
   - `file_path`: ruta API del binario (`/api/kbs/{kb_id}/documents/{document_id}/file`); peticiones con **Authorization: Bearer**; sin JWT fijo en query string.
3. **Markdown:** enlaces permitidos solo si el backend inyecta la URL o un `citation_ref` que el frontend resuelve; lista blanca de `href` y bloqueo de `javascript:` en `12-security.md` §8.
4. **URLs firmadas:** `/file?sig=...&exp=...` de corta duración como variante en `12-security.md` §7.3.
5. **Múltiples archivos:** el contexto puede mezclar chunks de varios documentos de una KB (filtro `kb_id`). El arreglo `citations` lleva una entrada por fuente usada (o por deduplicación top-M por documento, según política). Cada elemento tiene `document_id`, `viewer_path` y `file_path` propios.

### 7.5 Dónde se almacenan los documentos (binarios vs metadatos)

| Capa | Tecnología | Qué guarda |
|------|------------|------------|
| **Metadatos y control** | **PostgreSQL** | Tabla `documents`: nombre original, MIME, tamaño, hash, estado de ingesta, `kb_id`, y **`storage_path`** (ruta interna al archivo en disco, no pública). Tabla `chunks` y `message_citations` para texto fragmentado, páginas y trazabilidad. |
| **Archivo subido (binario)** | **Sistema de archivos en volumen Docker** (o ruta equivalente en servidor) | El PDF/DOCX/TXT tal cual se subió; solo **backend/worker** leen/escriben; el cliente accede vía `GET .../documents/{id}/file` con autenticación. |
| **Búsqueda semántica** | **Qdrant** | Vectores por chunk + **payload** con `doc_id`, `kb_id`, `page_start`/`page_end`, etc.; no sustituye el almacenamiento del binario. |

Diseño **local-first:** binarios en volumen y metadatos en PostgreSQL; object storage (S3, Azure Blob, etc.) queda fuera del alcance base. Una migración futura reemplaza la resolución de `storage_path` y la implementación interna de `/file` sin cambiar el contrato JSON expuesto al cliente.

---

## 8) Protección contra prompt injection

**Implementación (rama `feat/security-prompt-guards`):** `app/services/chat/prompt_guards.py` filtra chunks con patrones de inyección, sanitiza snippets, bloquea consultas de exfiltración y persiste `safety_flags` en el mensaje assistant. Variables: `PROMPT_GUARD_ENABLED`, `PROMPT_GUARD_BLOCK_USER_EXFIL`, `PROMPT_GUARD_MAX_CHUNK_CHARS`. Pruebas: `scripts/test-prompt-guards.sh`.

### 8.1 Amenaza

Documentos subidos pueden contener texto malicioso como:

- “Ignora todas las instrucciones anteriores…”
- “Revela secretos del sistema…”
- “Ejecuta comandos…”

El modelo puede obedecer si el contexto se inyecta sin control.

### 8.2 Estrategias (defensa en profundidad)

#### A) Etiquetar contexto como no confiable

En el prompt:

- Contexto = “fuentes” externas
- Prohibir seguir instrucciones dentro de documentos

#### B) Sanitización de contexto

Antes de pasar chunks al LLM:

- Eliminar/neutralizar patrones típicos:
  - “ignore previous instructions”
  - “system prompt”
  - “developer message”
  - “tools”
- Limitar longitud por chunk y total contexto.
- Remover bloques que parezcan instrucciones operativas.

#### C) Clasificación/heurísticas

Marcar chunks con flags:

- `injection_suspected=true` si se detectan patrones
- reducir score o excluirlos del contexto

#### D) Reglas de respuesta

Si el usuario pide:

- secretos, credenciales, llaves
- instrucciones para explotar el sistema

Entonces:

- rechazar con respuesta segura (en español) y sin revelar contenido interno.

#### E) “Grounding”

La respuesta cita evidencia en los chunks recuperados.

- Sin chunks relevantes, mensaje tipo: “No encuentro evidencia en los documentos cargados…”

---

## 9) Post-procesamiento de salida

### 9.1 Sanitización para UI

Render Markdown:

- HTML: sin `<script>` ni tags fuera de lista blanca
- enlaces: esquemas permitidos; `javascript:` excluido

### 9.2 Extracción de citas

- El backend construye citas a partir de top-M chunks usados.
- La precisión de documento/página no depende de que el LLM genere referencias por su cuenta.

### 9.3 Citas con hipervínculo en la interfaz

- Tras generar la respuesta (o en paralelo al streaming), el backend devuelve un arreglo estructurado de citas (REST y/o evento Socket.IO `chat:citation`) con `viewer_path`, `file_path`, `filename_original`, `page_start`, `page_end` y `mime_type`.
- El componente de chat renderiza cada fuente como enlace a `viewer_path` o botón “Descargar” contra `file_path`.
- Para PDF en el visor interno, **PDF.js** interpreta el query `page` (o estado inicial) para mostrar la página correcta.

### 9.4 Apertura del documento desde la interfaz

1. **Fuentes:** bajo el mensaje del asistente, cada cita incluye texto legible (archivo, “pág. N”) y enlace a `viewer_path` (ruta interna de la SPA, no path del volumen).
2. **Ruta visor:** ejemplo `/kbs/{kb_id}/documents/{document_id}?page=3`; el query `page` fija la página inicial en PDF; en otros MIME puede omitirse o asociarse solo a descarga.
3. **Binario:** `fetch(file_path)` con `Authorization: Bearer <access_token>` (o esquema de cookie definido en el proyecto); cuerpo: stream con `Content-Type` del documento.
4. **Render:** PDF → **PDF.js** sobre blob/arrayBuffer, vista en la página indicada; DOCX/TXT → descarga o vista simplificada; salto a página en DOCX no garantizado sin PDF (§7.4).
5. **Descarga:** `file_path` con `disposition=attachment` si el API lo expone, o blob en cliente tras `fetch` autenticado.

**Exposición:** sin URL anónima al archivo; acceso bajo sesión autenticada o URL firmada de vida corta (`12-security.md` §7.3).

---

## 10) Métricas recomendadas (para Prometheus/Grafana)

- Latencia por etapa:
  - `ingest_parse_ms`, `ingest_ocr_ms`, `ingest_embed_ms`, `qdrant_upsert_ms`
- Retrieval:
  - `retrieval_vector_ms`, `retrieval_bm25_ms`, `rerank_ms`
- Chat:
  - `llm_first_token_ms`, `llm_total_ms`, `tokens_out`
- Calidad (proxy):
  - % respuestas con citas
  - % “no evidencia encontrada”
  - top tags/sources consultados

---

## Checklist de implementación (RAG core)

- [ ] Configuración de chunking con hash/versión
- [ ] Embeddings con batching y límites de concurrencia
- [ ] Upsert Qdrant con payload completo
- [x] Hybrid retrieval (vector + BM25) — `feat/retrieval-hybrid`: RRF, BM25 en memoria por KB, `POST /api/kbs/{kb_id}/search`.
- [x] Reranking FlashRank — `feat/rerank-flashrank`: FlashRank opcional (`pip install -e '.[rerank]'`), fake en `ENVIRONMENT=test`.
- [ ] Filtrado por metadatos server-side
- [ ] Prompt seguro (español + grounding + anti-injection)
- [ ] Streaming y persistencia de chat + citas
- [ ] Citas con enlaces a visor/descarga y salto a página (PDF); límites documentados para DOCX/TXT

