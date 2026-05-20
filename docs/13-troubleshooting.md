# Troubleshooting (WSL2, Docker, Ollama, Qdrant, memoria, performance)

**Alcance:** problemas frecuentes y diagnóstico en despliegue local Windows 11 + WSL2 + Docker Compose.

---

## 1) Problemas con Docker Desktop / Docker Compose

### Síntoma: `The command 'docker' could not be found in this WSL 2 distro`

**Causa:** Docker Desktop está en Windows pero **no está la integración WSL** activada para tu distro Ubuntu, o Docker Desktop no está en ejecución.

**Solución (resumen)**

1. Abre **Docker Desktop** en Windows.
2. **Settings → General**: “Use the WSL 2 based engine” activado.
3. **Settings → Resources → WSL integration**: activa tu distro (p. ej. Ubuntu).
4. En PowerShell: `wsl --shutdown` → reinicia Docker Desktop → abre de nuevo la terminal WSL.
5. En WSL: `docker version` y `docker compose version`.

Detalle paso a paso: `docs/01-deployment.md` §3.

### Síntoma: `docker: Cannot connect to the Docker daemon`

**Causas comunes**

- Docker Desktop no está iniciado
- Integración WSL2 no está habilitada para Ubuntu

**Solución**

- Inicia Docker Desktop
- Habilita:
  - Settings → General → “Use the WSL 2 based engine”
  - Settings → Resources → WSL Integration → Ubuntu-22.04
- Reinicia:
  - `wsl --shutdown`
  - reinicia Docker Desktop

### Síntoma: `429 Too Many Requests` / `toomanyrequests` al hacer `docker compose build` o `docker pull`

**Causa:** Docker Hub limita descargas **anónimas** por dirección IP (y a veces por ventana de tiempo). Al cambiar de tag de imagen (`nginx:stable-alpine`, etc.) el motor pide un **manifest nuevo** y cuenta como pull.

**Solución (recomendada)**

1. Crea una cuenta gratuita en [Docker Hub](https://hub.docker.com/) si no tienes.
2. En **WSL** (o PowerShell, con el mismo Docker Desktop):

   ```bash
   docker login
   ```

   Usa tu usuario de Hub y, si te lo pide, un **Personal Access Token** como contraseña (mejor que la contraseña de la web).

3. Repite el build:

   ```bash
   docker compose build --pull frontend backend
   ```

**Alternativas:** esperar a que caduque la ventana del límite; usar otra red (otra IP); en equipos de empresa, un **registry mirror** o política de IT. Más información: [Increase rate limits](https://www.docker.com/increase-rate-limit).

### Síntoma: Contenedores “Restarting” continuamente

**Diagnóstico**

- Ver logs:

```bash
docker compose logs -f --tail=200
```

**Causas comunes**

- variables `.env` faltantes
- puertos en conflicto
- permisos en volúmenes
- Postgres no puede iniciar por datos corruptos

**Solución**

- Verifica `.env` con `docs/04-env-example.md`
- Cambia puertos expuestos en `docker-compose.yml` si hay conflicto
- Si estás en dev y puedes resetear (destructivo):

```bash
docker compose down -v
docker compose up -d
```

---

## 2) Problemas WSL2

### Síntoma: Git `fatal: detected dubious ownership in repository at '/mnt/c/...'`

**Causa:** el repositorio vive en NTFS montado como `/mnt/c/...` y el UID/GID de Windows no coincide con tu usuario Linux; Git 2.35+ trata el directorio como no confiable.

**Solución:** marcar el directorio como seguro (ajusta la ruta a tu repo):

```bash
git config --global --add safe.directory '/mnt/c/Users/flox_/OneDrive - Universidad de Monterrey/Proyectos personales/RAG Local'
```

Más contexto: `docs/01-deployment.md` §3 (Git en WSL con repo en `/mnt/c`).

### Síntoma: `curl http://localhost/health` devuelve 404 con el stack “supuestamente” arriba

**Causas comunes**

- **Docker no corre en WSL** (sin `docker compose up`): no hay Traefik del proyecto escuchando en el 80; otro programa en Windows puede responder con 404.
- El stack no está levantado: comprueba en Windows `docker compose ps` desde la misma carpeta del proyecto **o** en WSL tras arreglar la integración.

**Solución**

1. Arregla Docker en WSL (apartado anterior) y ejecuta `docker compose up -d --build` desde la raíz del repo.
2. `docker compose ps` → `traefik` y `frontend` en estado `running`.
3. Repite `curl -fsS http://localhost/health` (desde WSL o PowerShell; en WSL, `localhost` suele reenviarse al mismo host que Docker Desktop).

### Uploads: volumen `rag_vol_uploads`, `uploads/` en el host y ownership (WSL)

**Contexto**

- En **Docker Compose**, el servicio `worker` monta el volumen nombrado `rag_vol_uploads` en `/uploads` (datos bajo control del motor Docker; el UID dentro del contenedor suele ser root `0:0` u otro usuario de la imagen).
- Si ejecutas el **backend FastAPI en el host (WSL)** con `UPLOAD_STORAGE_DIR` vacío, los archivos se escriben en **`<repo>/uploads/`** con el UID de tu usuario WSL (p. ej. `1000:1000`). Eso es correcto para desarrollo local sin Docker para el API.

**Cuándo importa el “ownership”**

- Si más adelante **montas la misma carpeta del host** en un contenedor (bind mount) y el proceso del contenedor **no** coincide con tu UID, puedes ver `Permission denied` al leer/escribir o archivos creados como `root` en el host.
- Con **solo volumen nombrado** (`rag_vol_uploads`) y API en host **sin** compartir carpeta: no hay conflicto habitual; el worker y el API no comparten filesystem salvo que tú lo configures.

**Cómo comprobarlo (manual)**

1. **Volumen Docker** (con stack arriba):

   ```bash
   docker compose up -d worker
   docker exec rag_worker ls -la /uploads
   ```

   Deberías ver `/uploads` accesible; el propietario depende de la imagen (suele ser `root`).

2. **Carpeta del repo en WSL** (API local con `uvicorn`):

   ```bash
   ls -la uploads
   touch uploads/.perm_test && rm uploads/.perm_test
   ```

   Tras un upload por API, comprueba que los ficheros bajo `uploads/<uuid-kb>/` pertenecen a tu usuario (`ls -la uploads/...`).

3. **Si necesitas alinear UID en un bind mount** (solo si enlazas host → contenedor): ajusta `user:` en el servicio en `docker-compose.yml` al UID/GID de WSL (`id -u` / `id -g`) o usa `chown` en el host de forma consciente (documenta el procedimiento en tu entorno).

**Referencia:** `docker/CONVENTIONS.md` (volumen `rag_vol_uploads`), `docs/04-env-example.md` (`UPLOAD_STORAGE_DIR`).

### Síntoma: Lentitud extrema al instalar dependencias (node_modules, pip)

**Causa común**

- Repositorio en `/mnt/c/...` (filesystem Windows) con I/O lento para workloads Linux.

**Solución**

- Mueve el repo al filesystem Linux:
  - `~/projects/rag-local`

### Síntoma: `error: externally-managed-environment` al usar `pip install` en Ubuntu

**Causa:** Python del sistema está protegido (PEP 668); no se debe instalar paquetes de proyecto en el intérprete global.

**Solución:** crear un entorno virtual en `backend/` (u otra ruta) y usar su `pip`:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Si falla `python3 -m venv`, instala `python3-venv` / `python3-full` (ver `docs/01-deployment.md`).

### Síntoma: `npm` abre rutas `\\wsl.localhost\...` o escribe logs en `C:\Users\...` desde una terminal WSL

**Causa:** estás usando el **npm de Windows** (p. ej. bajo `/mnt/c/nvm4w/...`) en lugar del npm del propio Linux.

**Solución:** instala Node/npm en la distro (`sudo apt install npm` o **nvm/fnm dentro de WSL**). Comprueba `which npm` → debe ser una ruta bajo `/usr/...` o `~/.nvm/...`, no `/mnt/c/...`.

### Síntoma: WSL se queda sin memoria / el sistema se “congela”

**Diagnóstico**

- Revisa consumo en Windows Task Manager y dentro de WSL:

```bash
free -h
top
```

**Solución**

- Ajusta `%UserProfile%\.wslconfig`:
  - `memory`
  - `swap`
  - `processors`
- Reduce concurrencia del worker:
  - `CELERY_WORKER_CONCURRENCY`
- Reduce batch embeddings:
  - `EMBEDDING_BATCH_SIZE`

---

## 3) Ollama issues

### Síntoma: `ollama` responde pero el modelo no existe

**Diagnóstico**

```bash
curl -s http://localhost:11434/api/tags | jq
```

**Solución**

- Descargar modelo (dependiendo de tu setup):

```bash
docker compose exec ollama ollama pull qwen2.5:7b-instruct
```

### Síntoma: Respuestas lentas / latencia alta

**Causas**

- CPU-only
- contexto muy grande
- streaming activado pero redirección/proxy mal

**Mitigaciones**

- Reducir contexto (top_k/rerank_top_k)
- Reducir `LLM_MAX_TOKENS`
- Ajustar `CHUNK_SIZE_TOKENS` y número de chunks

---

## 4) Qdrant issues

### Síntoma: Qdrant no inicia

**Diagnóstico**

```bash
docker compose logs -f --tail=200 qdrant
```

**Causas**

- volumen corrupto
- permisos

**Solución**

- En dev, reset del volumen Qdrant (destructivo):

```bash
docker compose down -v
docker compose up -d
```

### Síntoma: ingesta `FAILED` con `qdrant_dimension_mismatch`

**Causa**

La colección `QDRANT_COLLECTION` (p. ej. `rag_chunks_v1`) se creó con un modelo de embeddings de **otra dimensión** (típico: pruebas con `EMBEDDING_BACKEND=fake` → 64 dims) y ahora usas **BGE-M3** u otro modelo (p. ej. **1024** dims).

**Solución (dev local)**

1. Borra la colección y reindexa:

```bash
bash scripts/reset-qdrant-collection.sh
```

2. Con el worker en marcha, **reindexa** cada PDF (`POST .../documents/{id}/reindex` o botón en UI).

3. Comprueba que el documento pase a `READY` y que `embed` / `qdrant_upsert` estén en DONE.

**Prevención**

- No mezclar `fake` y `sentence_transformers` sobre la misma colección Qdrant sin reset.
- En `.env` deja fijo `EMBEDDING_MODEL_NAME=BAAI/bge-m3` y `EMBEDDING_BACKEND=auto` (o `sentence_transformers`).

### Síntoma: Retrieval no encuentra nada aunque hay documentos “READY”

**Diagnóstico**

- Verifica:
  - `documents.status=READY`
  - `chunks` existen
  - `qdrant_point_id` poblado
- Revisa filtros:
  - `kb_id` correcto
  - tags/source no demasiado restrictivos

**Solución**

- Reindexar documento/Kb (cuando exista endpoint/script)
- Reducir filtros
- Verificar colección `QDRANT_COLLECTION`

---

## 5) Redis / Celery issues

### Síntoma: Ingesta se queda en `UPLOADED` y nunca avanza

**Diagnóstico**

- Worker no está corriendo
- Celery no conecta a Redis

Comandos:

```bash
docker compose ps
docker compose logs -f --tail=200 worker
docker compose logs -f --tail=200 redis
```

**Solución**

- Verifica `CELERY_BROKER_URL`
- Asegura que el worker esté en `up`

---

## 6) Problemas de parsing/OCR

### Síntoma: PDF con texto “vacío”

**Causa**

- PDF escaneado: texto no seleccionable

**Solución**

- Habilitar OCR:
  - `OCR_ENABLED=true`
- Asegurar idioma:
  - `TESSERACT_LANGS=spa`

### Síntoma: OCR extremadamente lento

**Mitigaciones**

- Limitar OCR a páginas necesarias
- Reducir concurrencia OCR
- Cachear resultados
- Hacer “early exit” si se detecta suficiente texto extraído

---

## 7) Problemas de memoria / performance (embeddings)

### Síntoma: Worker se mata (OOMKilled) durante embeddings

**Causas**

- batch size muy alto
- demasiada concurrencia
- documento muy grande

**Solución**

- Bajar:
  - `EMBEDDING_BATCH_SIZE` (p. ej. 32 → 16 → 8)
  - `CELERY_WORKER_CONCURRENCY` (p. ej. 4 → 2)
- Procesar por páginas o por lotes de chunks

---

## 8) Frontend no puede conectar al backend / CORS

### Síntoma: errores CORS en navegador

**Diagnóstico**

- Revisa `CORS_ALLOW_ORIGINS`
- Verifica que el frontend use `PUBLIC_API_BASE_URL` correcto

**Solución**

- Agrega `http://localhost` y el puerto real si aplica
- Reinicia servicios:

```bash
docker compose restart backend frontend
```

---

## 9) Socket.IO / streaming no funciona

### Síntoma: el chat responde pero no streamea tokens

**Causas**

- Proxy no enruta `/socket.io`
- CORS/WebSocket headers incorrectos

**Diagnóstico**

- Ver logs backend/traefik:

```bash
docker compose logs -f --tail=200 backend
docker compose logs -f --tail=200 traefik
```

**Solución**

- Asegurar rutas en Traefik:
  - `/socket.io` → backend
- Verificar que el cliente use la misma base URL

---

## 10) Recomendación final: checklist de diagnóstico rápido

- [ ] `docker compose ps` muestra servicios `Up`
- [ ] `GET /api/health` responde `200` o `503` con dependencias explícitas
- [ ] Redis accesible desde backend/worker
- [ ] Qdrant accesible desde backend/worker
- [ ] Ollama responde y el modelo existe
- [ ] `.env` completo y consistente
- [ ] recursos WSL2 suficientes (RAM/swap)

