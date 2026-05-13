# Despliegue local (WSL2 + Docker Compose)

Preparación de entorno **100% local** en Windows 11 con **WSL2 (Ubuntu 22.04)** y **Docker Desktop**, y arranque con **Docker Compose**.

**Reproducibilidad:** clon del repositorio, archivo `.env`, comando `docker compose up -d`, comprobación de salud de servicios.

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

El runtime principal es Docker; el paquete anterior cubre scripts locales, depuración y utilidades en WSL.

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

Rutas montadas desde Windows (`/mnt/c/...`): mayor latencia en `node_modules`, watchers e I/O frecuente; el filesystem nativo de WSL reduce el problema.

---

## 5) Preparar variables de entorno

1. Archivo `.env` en la raíz del repositorio.
2. Valores de partida en `env-example.md`.
3. Variables típicas:
   - secretos JWT
   - credenciales de Postgres
   - configuración de CORS/orígenes
   - límites de upload
   - parámetros RAG (topK, thresholds, etc.)

---

## 6) Estructura esperada de carpetas (local)

Estructura prevista en la raíz (creación según fase del proyecto):

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

Los identificadores de modelo (`qwen2.5:7b-instruct`, etc.) dependen del catálogo de la instancia Ollama en uso.

---

## 11) Buenas prácticas de operación local

- **Persistencia**: usa volúmenes Docker para Postgres/Qdrant/Grafana.
- **Backups**:
  - Postgres: `pg_dump`
  - Qdrant: snapshots (si se habilitan)
  - Uploads: copia de `uploads/`
- **Actualizaciones**:
  - `docker compose pull` y `docker compose up -d`
- **Recursos:** uso de RAM/CPU elevado durante OCR y embeddings.

---

## 12) Troubleshooting rápido (enlaces)

- Docker/WSL2: `troubleshooting.md`
- Seguridad, WAF, uploads: `security.md`

