# Troubleshooting (WSL2, Docker, Ollama, Qdrant, memoria, performance)

Este documento lista problemas comunes y pasos de diagnóstico para un despliegue local en Windows 11 + WSL2 + Docker Compose.

---

## 1) Problemas con Docker Desktop / Docker Compose

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

- Verifica `.env` con `docs/env-example.md`
- Cambia puertos expuestos en `docker-compose.yml` si hay conflicto
- Si estás en dev y puedes resetear (destructivo):

```bash
docker compose down -v
docker compose up -d
```

---

## 2) Problemas WSL2

### Síntoma: Lentitud extrema al instalar dependencias (node_modules, pip)

**Causa común**

- Repositorio en `/mnt/c/...` (filesystem Windows) con I/O lento para workloads Linux.

**Solución**

- Mueve el repo al filesystem Linux:
  - `~/projects/rag-local`

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

