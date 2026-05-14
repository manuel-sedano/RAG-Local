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

1. Instala **Docker Desktop** en Windows y ábrelo (debe quedar en ejecución).
2. En Docker Desktop:
   - **Settings → General**: habilita **“Use the WSL 2 based engine”**.
   - **Settings → Resources → WSL integration**:
     - Activa **“Enable integration with my default WSL distro”** (si aparece), y/o
     - Activa explícitamente tu distro (p. ej. **Ubuntu** o **Ubuntu-22.04**) en la lista.
3. Aplica y reinicia si el programa lo pide; si sigue fallando, en **PowerShell** (Windows):

   ```powershell
   wsl --shutdown
   ```

   Luego vuelve a abrir **Docker Desktop** y espera a que arranque por completo.

4. Verifica **desde la terminal de Ubuntu (WSL)** (no solo desde PowerShell):

```bash
docker version
docker compose version
```

### Síntoma: `The command 'docker' could not be found in this WSL 2 distro`

Significa que **en esa distro WSL no está instalado el cliente Docker** (Docker Desktop no ha inyectado el binario) o la integración está desactivada.

1. Confirma que Docker Desktop está **abierto** y sin errores en la bandeja.
2. **Settings → Resources → WSL integration**: activa tu distro exacta (el nombre que sale en `wsl -l -v`).
3. `wsl --shutdown` en PowerShell → abre de nuevo Ubuntu y Docker Desktop.
4. Vuelve a ejecutar `docker version` dentro de WSL.

**Alternativa (no recomendada para este proyecto):** instalar `docker.io` con `apt` dentro de WSL; duplica el motor y choca con Docker Desktop. Para este repo se asume **solo Docker Desktop + integración WSL**.

### Síntoma: Git `fatal: detected dubious ownership in repository at '/mnt/c/...'`

Ocurre cuando el repo está en **disco Windows** (`/mnt/c/...`) y el propietario de los archivos no coincide con tu usuario Linux en WSL. Git bloquea el acceso por seguridad.

En **WSL** (ajusta la ruta si es distinta):

```bash
git config --global --add safe.directory '/mnt/c/Users/flox_/OneDrive - Universidad de Monterrey/Proyectos personales/RAG Local'
```

O, solo para este repo y sin fijar la ruta absoluta (útil si cambias de ruta):

```bash
git config --global --add safe.directory '*'
```

La opción `'*'` es más permisiva; úsala solo si entiendes el riesgo en máquinas compartidas.

---

## 4) Ubicación del repositorio (clon o ruta actual)

### 4a) Recomendado: clonar en filesystem Linux (`~/...`)

Mejor rendimiento (menos latencia que `/mnt/c/...`, especialmente con `node_modules`, watchers y builds):

```bash
mkdir -p ~/projects && cd ~/projects
git clone <URL_DEL_REPO> rag-local
cd rag-local
git checkout develop
git pull origin develop
```

Sustituye `<URL_DEL_REPO>` por la URL HTTPS o SSH del remoto (la misma que usarías en GitHub).

### 4b) Si ya estás en WSL bajo `/mnt/c/...` (OneDrive o disco Windows)

Es válido para arrancar Docker Compose; el proyecto documenta que **I/O y sincronización** (OneDrive) pueden hacer más lentos builds y Git. Para trabajo diario, preferir **4c** cuando puedas.

Desde tu ruta actual (ajusta si tu usuario o carpeta difieren):

```bash
cd "/mnt/c/Users/flox_/OneDrive - Universidad de Monterrey/Proyectos personales/RAG Local"

# Si Git avisa "dubious ownership" en repos bajo /mnt/c/:
git config --global --add safe.directory '/mnt/c/Users/flox_/OneDrive - Universidad de Monterrey/Proyectos personales/RAG Local'

git fetch origin
git checkout develop
git pull origin develop

mkdir -p uploads

docker compose up -d --build
docker compose ps
```

Comprobaciones rápidas (mismo criterio que `docs/02-smoke-test.md`):

```bash
curl -fsS http://localhost/health
curl -fsS http://localhost/api/health
docker compose exec postgres pg_isready -U rag -d rag
docker compose exec redis redis-cli ping
```

**`.env`:** con el **bootstrap** actual (placeholders), el `docker-compose.yml` trae valores de demo en servicios; no es obligatorio un `.env` solo para levantar el stack. Cuando exista backend real, crea `.env` en la raíz siguiendo `docs/04-env-example.md` (el archivo `.env` no se versiona).

### 4c) Migración recomendada desde `/mnt/c/` a `~/projects/` (misma máquina)

En el repo “viejo” obtén la URL del remoto:

```bash
cd "/mnt/c/Users/flox_/OneDrive - Universidad de Monterrey/Proyectos personales/RAG Local"
git remote -v
```

En una ruta bajo Linux (ext4):

```bash
mkdir -p ~/projects && cd ~/projects
git clone <URL_QUE_COPIASTE> rag-local
cd rag-local
git checkout develop
git pull origin develop
```

Si ya tenías un `.env` en la ruta de Windows, cópialo (no lo subas a Git):

```bash
cp "/mnt/c/Users/flox_/OneDrive - Universidad de Monterrey/Proyectos personales/RAG Local/.env" ~/projects/rag-local/.env
# solo si el archivo existía
```

Luego trabaja siempre desde `~/projects/rag-local` para `git` y `docker compose`.

---

## 5) Preparar variables de entorno

1. Archivo `.env` en la raíz del repositorio.
2. Valores de partida en `04-env-example.md`.
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

La lista canónica de comandos está en **`docs/02-smoke-test.md`**. Resumen alineado al stack actual:

### 8.1 Frontend (Traefik → servicio `frontend`)

- Navegador: `http://localhost/`
- Salud: `curl -fsS http://localhost/health` → cuerpo `ok`

### 8.2 Backend placeholder

- `curl -fsS http://localhost/api/health` → JSON con `"status":"ok"` (sin comprobar aún dependencias; eso vendrá con el backend FastAPI).

### 8.3 Qdrant (solo red interna en el bootstrap)

No hay puerto `6333` publicado al host. Desde un contenedor en `rag_net`:

```bash
docker compose exec backend wget -qO- http://qdrant:6333/ready
```

### 8.4 Ollama (solo red interna en el bootstrap)

`localhost:11434` no está mapeado al host. Ejemplo:

```bash
docker compose exec backend wget -qO- http://ollama:11434/api/tags
```

(Cuando tengas modelos descargados, verás entradas en `models`.)

### 8.5 Observabilidad (perfil `observability`)

Levantar antes:

```bash
docker compose --profile observability up -d
```

- Grafana: `http://localhost/grafana/` (credenciales por defecto del compose; cámbialas fuera de entornos locales).
- Prometheus: `http://localhost/prometheus/` (UI detrás de Traefik).
- Loki: comprobar readiness por red interna (ver `docs/02-smoke-test.md`).

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

- Docker/WSL2: `13-troubleshooting.md`
- Seguridad, WAF, uploads: `12-security.md`

