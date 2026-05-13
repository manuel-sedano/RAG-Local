# Seguridad (Auth, uploads, WAF, rate limiting, logging, prompt injection)

**Alcance:** controles para una plataforma RAG local con **uploads**, exposición web (UI + API), pipelines (parsing, OCR, embeddings) e invocación de LLM con contexto recuperado (prompt injection).

**Objetivos:** superficie de ataque reducida; integridad de host y datos; trazabilidad y auditoría; mitigación de abuso (DoS, fuerza bruta, scraping); configuración **secure-by-default**.

---

## 1) Modelo de amenazas (alto nivel)

### Actores y riesgos

- **Usuario legítimo**:
  - accidentalmente sube archivo malicioso
  - ejecuta queries que disparan carga excesiva
- **Usuario autenticado malicioso**:
  - intenta exfiltrar datos de otras KB
  - intenta prompt injection para extraer secretos o instrucciones
  - sube archivos con payloads para explotar parsers
- **Atacante externo (sin auth)**:
  - brute-force login
  - scanning de endpoints
  - DoS por volumen de requests

### Superficies críticas

- Upload endpoint (`multipart`)
- Parsing/OCR (bibliotecas complejas)
- Streaming / sockets
- Reverse proxy / WAF config
- RAG context + prompting (prompt injection)

---

## 2) Autenticación y autorización

### 2.1 JWT (access + refresh)

Recomendación:

- Access token:
  - TTL corto (ej. 15 min)
  - scope/claims mínimos
- Refresh token:
  - TTL más largo (ej. 7–30 días)
  - **rotación** en cada refresh
  - revocación (logout, compromise)

Claims sugeridos (access):

- `sub` = `user_id`
- `role`
- `iat`, `exp`
- `jti` (id token)

Controles:

- firma fuerte (`HS256` con secret largo o `RS256` con llaves)
- clock skew controlado
- blacklist/allowlist de refresh tokens (hash en DB)

### 2.2 Almacenamiento de credenciales

- Hash de password con **Argon2id** (o bcrypt con costo alto).
- Nunca almacenar contraseñas en texto plano.
- Política:
  - longitud mínima
  - fuerza (opcional)
  - lockout progresivo

### 2.3 Autorización por KB

Reglas:

- En cada request con `kb_id`:
  - validar membresía/permisos server-side
- Prohibir que el cliente “decida” filtros que salten permisos:
  - `kb_id` forzado en retrieval y Qdrant filters
  - si multi-tenant, forzar `tenant_id`

---

## 3) Seguridad de uploads (alta prioridad)

### 3.1 Validación de archivos

Aplicar en `backend` antes de aceptar:

- límite de tamaño (`MAX_UPLOAD_MB`)
- allowlist de tipos:
  - PDF, DOCX, TXT
- validación de MIME real:
  - magic bytes (preferido) + encabezados
- nombre de archivo:
  - ignorar el nombre original para storage
  - generar UUID para evitar path traversal

### 3.2 Persistencia segura

- Guardar en `uploads/` dentro de un volumen:
  - permisos estrictos (solo contenedores backend/worker)
- NUNCA ejecutar ni abrir directamente el archivo subido.
- “Quarantine”:
  - si antivirus sospecha, mover a zona de cuarentena
  - marcar `status=QUARANTINED`

### 3.3 Antivirus (ClamAV)

Flujo recomendado:

1. Subida → guardar temporalmente
2. Worker escanea con `clamd`
3. Si OK:
   - continuar parsing
4. Si detecta malware:
   - marcar QUARANTINED
   - registrar `security_event`
   - bloquear acceso/descarga del binario

### 3.4 Protección contra “zip bombs” / “parser bombs”

Aunque solo aceptes PDF/DOCX/TXT:

- DOCX es un zip: limitar:
  - tamaño comprimido vs descomprimido
  - número de entradas
- Timeouts estrictos en parsing/OCR:
  - si excede, abortar y marcar FAILED

### 3.5 OCR y parsing en sandbox (recomendación)

Minimizar impacto:

- correr OCR/parsers en contenedor worker aislado
- limites de recursos:
  - CPU/memoria (Compose `deploy` no aplica igual; usar `mem_limit` donde aplique)
- no montar directorios sensibles del host

---

## 4) WAF (ModSecurity + OWASP CRS)

### 4.1 Objetivo

Bloquear ataques comunes:

- SQLi
- XSS
- RCE payloads
- path traversal
- request smuggling patterns

### 4.2 Posicionamiento

Topología recomendada:

- Cliente → Traefik → (WAF) → Backend

### 4.3 Ajustes recomendados

- Modo “DetectionOnly” inicial para observar falsos positivos.
- Luego “On” (bloqueo) con:
  - exceptions por endpoints de upload (sin relajar demasiado)
  - límites por body size

---

## 5) Rate limiting y anti-abuso

### 5.1 En Traefik (perimeter)

Rate limit por IP:

- `/api/auth/login`: muy estricto
- `/api/*`: moderado
- `/socket.io`: control de conexiones concurrentes

### 5.2 En backend (application-level)

Usar Redis para:

- rate limit por usuario
- rate limit por KB
- cuotas de ingestion:
  - max documentos por minuto
  - max OCR jobs concurrentes

### 5.3 Protección contra brute-force

Capas:

- rate limit login
- lockout por usuario (p. ej. 10 intentos → cooldown)
- Fail2ban leyendo logs (si se configura)

---

## 6) Logging, auditoría y trazabilidad

### 6.1 Logs (Loki)

Campos habituales en logs estructurados:

- `request_id` por request
- `user_id` (si autenticado)
- `kb_id` cuando aplique
- latencias por etapa
- outcome (status code, error_code)

Nunca loggear:

- tokens JWT completos
- contraseñas
- secretos

### 6.2 Auditoría (Postgres)

Registrar eventos:

- login exitoso/fallido
- virus detectado
- WAF blocks
- eliminación de documentos/KB
- reindexados

---

## 7) Seguridad del RAG: prompt injection y data exfiltration

### 7.1 Principio clave

El contenido recuperado de documentos es **no confiable**. Puede contener instrucciones para manipular al modelo.

### 7.2 Controles recomendados

#### A) Prompt seguro (system)

Contenido típico del system prompt:

- idioma de salida: español
- instrucciones incrustadas en documentos de usuario: no tienen prioridad sobre la política del sistema
- salida anclada a evidencia en chunks recuperados
- plantilla de respuesta cuando no hay evidencia recuperada

#### B) Sanitización de chunks

Antes de enviar al LLM:

- recortar longitud
- eliminar patrones típicos de inyección
- etiquetar origen: `DOC:` y metadatos

#### C) “Grounding enforcement”

- Sin chunks por encima del umbral de relevancia: mensaje tipo “No encuentro evidencia en los documentos cargados…”
- Sin fuentes en contexto: sin afirmaciones presentadas como hechos verificados en corpus.

#### D) Filtrado de solicitud del usuario

Patrones de solicitud con bloqueo o advertencia:

- petición de credenciales/secretos
- intento de extraer system prompt
- instrucciones para evadir seguridad

#### E) Minimizar información del sistema

Exclusión típica de la salida al cliente:

- paths internos
- nombres de servicios internos
- logs crudos

### 7.3 Descarga y visualización de documentos citados (auth)

- Archivos subidos: sin URL estática pública ni rutas de disco predecibles sin sesión.
- Acceso al binario: **`GET /api/kbs/{kb_id}/documents/{doc_id}/file`** con **JWT** y comprobación de membresía en la KB (`api-spec.md`).
- Hipervínculos en el chat: **rutas internas** (`viewer_path`) → visor (p. ej. PDF.js) y obtención del PDF con el token de la SPA (`fetch` + blob/stream); sin enlaces anónimos al binario.
- **Opcional (hardening):** URLs firmadas de muy corta duración (`sig` + `exp`) solo si se requiere abrir el archivo en una pestaña sin cabecera `Authorization`; rotar clave de firma y registrar auditoría de emisión.

---

## 8) Seguridad del frontend

- **Markdown:** render con lista blanca de etiquetas; `href` restringido a rutas internas (`/...`) o esquemas controlados por la aplicación; HTML arbitrario fuera del pipeline de render.
- **XSS:** CSP cuando el despliegue lo permita; cabeceras endurecidas vía Traefik.
- **Tokens:** almacenamiento en `localStorage` frente a cookies `httpOnly` según modelo de amenaza y arquitectura; la elección queda registrada en la documentación del despliegue.

---

## 9) Configuración de red segura (Docker)

- **Host:** únicamente Traefik en 80/443 hacia el exterior.
- **Puertos no publicados hacia el host:** Postgres (5432), Redis (6379), Qdrant (6333/6334), Ollama (11434), Uvicorn directo.
- **Red:** bridge interna entre servicios.
- **Volúmenes:** montajes acotados desde el host; permisos mínimos en rutas de datos.

---

## 10) Checklist de seguridad (MVP)

- [ ] JWT access/refresh con rotación y revocación
- [ ] Password hashing Argon2id
- [ ] RBAC/membresía por KB
- [ ] Upload allowlist (PDF/DOCX/TXT) + magic bytes
- [ ] Límite de tamaño y rate limiting de upload
- [ ] Escaneo ClamAV y cuarentena
- [ ] WAF con OWASP CRS (DetectionOnly → Blocking)
- [ ] Rate limiting en Traefik + Redis por usuario
- [ ] Logs con request_id + auditoría de eventos
- [ ] Sanitización de Markdown y protección XSS
- [ ] Guardrails anti prompt injection + grounding con citas
- [ ] Archivos solo vía `GET .../documents/{id}/file` con auth; citas con `viewer_path` interno; sin JWT permanente en query string

