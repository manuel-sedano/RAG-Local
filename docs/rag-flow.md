# Flujo RAG (chunking → embeddings → retrieval → reranking → prompting)

Este documento explica el flujo completo de RAG para una plataforma local con:

- Chunking configurable
- Embeddings locales (bge-m3)
- Búsqueda híbrida (vector + BM25)
- Reranking (FlashRank)
- Prompting robusto
- Filtrado por metadatos
- Defensa contra prompt injection

El objetivo es que el sistema produzca respuestas **en español**, con **citas** y **trazabilidad**.

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

- Evitar rerank de cientos de chunks por performance.
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
  - página
  - identificador de chunk (para auditoría)

Ejemplo de respuesta deseada (en español):

> Según el documento de políticas de viáticos, los reembolsos requieren comprobantes válidos y autorización previa del supervisor.  
>
> **Fuentes:**  
> - Manual Finanzas 2026, pág. 3 (chunk 17)  
> - Manual Finanzas 2026, pág. 4 (chunk 22)

---

## 8) Protección contra prompt injection

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

Exigir que la respuesta cite evidencia:

- si no hay chunks relevantes, el sistema debe decir:
  - “No encuentro evidencia en los documentos cargados…”

---

## 9) Post-procesamiento de salida

### 9.1 Sanitización para UI

Si se renderiza Markdown:

- sanitizar HTML (no permitir `<script>`)
- lista blanca de tags/links
- deshabilitar `javascript:` en links

### 9.2 Extracción de citas

Estrategias:

- El backend construye citas a partir de top-M chunks usados.
- Evitar confiar en que el LLM “inventará” citas correctas.

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
- [ ] Hybrid retrieval (vector + BM25)
- [ ] Reranking FlashRank
- [ ] Filtrado por metadatos server-side
- [ ] Prompt seguro (español + grounding + anti-injection)
- [ ] Streaming y persistencia de chat + citas

