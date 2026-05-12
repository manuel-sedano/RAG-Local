# Despliegue local (WSL2 + Docker Compose)

Este documento describe cómo preparar un entorno **100% local** en Windows 11 usando **WSL2 (Ubuntu 22.04)** y **Docker Desktop**, y cómo levantar la plataforma con **Docker Compose**.

> Objetivo: reproducibilidad. Debes poder clonar el repo, crear `.env`, ejecutar `docker compose up -d` y verificar salud de servicios.

---

## Requisitos previos

### Hardware recomendado (referencia)

- CPU: Ryzen 7 5700X o similar
- RAM: 32GB
- Almacenamiento: NVMe con espacio libre suficiente (modelos + vectores + uploads)
- GPU: opcional; Ollama puede usar aceleración dependiendo del stack instalado

### Software requerido (Windows)

- Windows 11 actualizado
- PowerShell
- Docker Desktop (última versión estable)
- Git
- VS Code (opcional pero recomendado)

---

## 1) Instalar/activar WSL2

En PowerShell (Administrador):

```powershell
wsl --install
wsl --set-default-version 2
wsl --list --verbose
```

Instala Ubuntu 22.04 si no quedó instalado:

```powershell
wsl --install -d Ubuntu-22.04
```

Verifica que Ubuntu esté en WSL2:

```powershell
wsl -l -v
```

---

## 2) Configurar Ubuntu 22.04 (WSL2)

En la terminal de Ubuntu (WSL):

Actualizar paquetes:

```bash
sudo apt update && sudo apt upgrade -y
```

Instalar utilidades base:

```bash
sudo apt install -y \
  ca-certificates curl git unzip jq build-essential \
  python3 python3-venv python3-pip
```

> Nota: aunque el proyecto corre con Docker, estas herramientas ayudan para scripts, debugging y utilidades.

### (Recomendado) Configurar recursos de WSL

Para controlar memoria/CPU de WSL crea o edita `%UserProfile%\.wslconfig` (en Windows) con algo como:

```ini
[wsl2]
memory=24GB
processors=8
swap=8GB
```

Aplica cambios:

```powershell
wsl --shutdown
```

---

## 3) Instalar Docker Desktop y habilitar integración WSL2

1. Instala Docker Desktop.
2. En Docker Desktop:
   - **Settings → General**: habilita “Use the WSL 2 based engine”.
   - **Settings → Resources → WSL Integration**: habilita Ubuntu-22.04.
3. Verifica desde WSL:

```bash
docker version
docker compose version
```

Si falla, revisa:

- Docker Desktop está iniciado.
- WSL Integration habilitada.
- `wsl --shutdown` y reinicia Docker Desktop.

---

## 4) Clonar el repositorio

### Recomendación de ubicación

Para mejor performance, clona dentro del filesystem Linux (WSL), por ejemplo:

```bash
mkdir -p ~/projects && cd ~/projects
git clone <TU_URL_DEL_REPO> rag-local
cd rag-local
```

> Evita trabajar directo en rutas montadas de Windows (`/mnt/c/...`) si notas lentitud con node_modules, watch, o I/O intensivo.

---

## 5) Preparar variables de entorno

1. Crea `.env` en la raíz del repo.
2. Copia valores desde `docs/env-example.md`.
3. Ajusta:
   - secretos JWT
   - credenciales de Postgres
   - configuración de CORS/orígenes
   - límites de upload
   - parámetros RAG (topK, thresholds, etc.)

---

## 6) Estructura esperada de carpetas (local)

En la raíz del repo deben existir (se crearán según necesidad):

- `uploads/` (persistencia de archivos)
- `docker/` (configs traefik/waf/observabilidad)
- `scripts/` (scripts de mantenimiento)
- `frontend/` y `backend/` (código)

Si `uploads/` no existe, créala:

```bash
mkdir -p uploads
```

---

## 7) Arranque con Docker Compose

Desde la raíz del repo:

```bash
docker compose up -d
```

Ver logs:

```bash
docker compose logs -f --tail=200
```

Estado:

```bash
docker compose ps
```

Parar:

```bash
docker compose down
```

Parar y borrar volúmenes (destructivo, perderás datos):

```bash
docker compose down -v
```

---

## 8) Verificación (smoke tests)

### 8.1 Frontend

- Abre la URL local publicada por Traefik (por defecto):
  - `http://localhost/`

### 8.2 Backend

Endpoint de salud:

- `GET /api/health`

Esperado:

- `200 OK` con JSON indicando estado de dependencias (Postgres/Redis/Qdrant/Ollama).

### 8.3 Qdrant

Si se expone (opcional):

- `GET /qdrant/` o `http://localhost:6333/`

### 8.4 Ollama

Verifica que el contenedor esté arriba y que el modelo esté disponible.

Comando típico (dependiendo de cómo se integre):

```bash
curl -s http://localhost:11434/api/tags | jq
```

### 8.5 Observabilidad (opcional)

- Grafana: `http://localhost/grafana`
- Prometheus: `http://localhost/prometheus`
- Loki: `http://localhost/loki`

---

## 9) Inicialización de base de datos (cuando exista backend)

Cuando el backend esté implementado:

- Ejecutar migraciones Alembic en el contenedor backend:

```bash
docker compose exec backend alembic upgrade head
```

---

## 10) Descarga/carga de modelos (Ollama)

Cuando `ollama` esté configurado:

```bash
docker compose exec ollama ollama pull qwen2.5:7b-instruct
```

> Nota: los nombres exactos de tags dependen del catálogo de Ollama local. Ajusta según la versión instalada.

---

## 11) Buenas prácticas de operación local

- **Persistencia**: usa volúmenes Docker para Postgres/Qdrant/Grafana.
- **Backups**:
  - Postgres: `pg_dump`
  - Qdrant: snapshots (si se habilitan)
  - Uploads: copia de `uploads/`
- **Actualizaciones**:
  - `docker compose pull` y `docker compose up -d`
- **Recursos**: monitorea RAM/CPU durante OCR + embeddings.

---

## 12) Troubleshooting rápido (enlaces)

- Problemas Docker/WSL2: ver `docs/troubleshooting.md`
- Seguridad/WAF/uploads: ver `docs/security.md`

