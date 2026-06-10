# Smoke test mínimo (bootstrap Compose)

Objetivo: comprobar que el stack base arranca y que **solo Traefik** expone puertos **80/443** al host; el resto de servicios queda en la red interna `rag_net`.

**Requisitos:** Docker Engine + Docker Compose v2, idealmente en **WSL2** (Ubuntu) como indica el README del proyecto.

**Nota (dev tooling):** los servicios `frontend` y `backend` de este compose son **placeholders nginx**. La app **Next.js** real se prueba con `npm run dev` en `frontend/` (ver README, sección *Desarrollo local*).

---

## 1. Arranque base (sin perfiles opcionales)

Desde la raíz del repositorio:

```bash
docker compose up -d --build
```

Comprobar contenedores:

```bash
docker compose ps
```

---

## 2. Traefik y placeholders (HTTP :80)

- **Frontend placeholder** (HTML):

  ```bash
  curl -fsS http://localhost/ | head
  ```

- **Salud del frontend** (texto plano):

  ```bash
  curl -fsS http://localhost/health
  ```

  Debe responder `ok`.

- **API placeholder** (JSON detrás de Traefik en `/api`):

  ```bash
  curl -fsS http://localhost/api/health
  ```

  Debe devolver JSON con `"status":"ok"` y `"service":"backend-placeholder"`.

- **Traefik y Docker:** el bootstrap usa el **provider `file`** (`docker/traefik/dynamic/bootstrap.yml`) para enrutar a los servicios por nombre DNS interno, sin depender del socket Docker (evita 404 en entornos WSL + Docker Desktop donde el cliente embebido falla).

---

## 3. PostgreSQL y Redis (solo red interna)

No hay puertos publicados; se usa `docker compose exec`:

```bash
docker compose exec postgres pg_isready -U rag -d rag
docker compose exec redis redis-cli ping
```

Esperado: `accepting connections` y `PONG`.

---

## 4. Qdrant y Ollama (solo red interna)

```bash
docker compose exec backend wget -qO- http://qdrant:6333/ready
docker compose exec backend wget -qO- http://ollama:11434/api/tags
```

- Qdrant: respuesta vacía o JSON de estado listo (según versión).
- Ollama: JSON (lista de modelos; puede estar vacía `{"models":[]}` si aún no descargaste modelos).

---

## 5. Volumen de subidas (`rag_vol_uploads`)

El **worker** placeholder monta el volumen en `/uploads`:

```bash
docker compose exec worker sh -c 'touch /uploads/.smoke && ls -la /uploads'
```

Debe mostrarse el fichero `.smoke` (prueba de escritura en el volumen nombrado).

---

## 6. Perfil **ClamAV** (opcional)

Primer arranque puede tardar varios minutos (bases de firmas).

```bash
docker compose --profile clamav up -d clamav
./scripts/test-clamav.sh
```

Comprobar que `rag_clamav` pasa a **healthy** (la primera descarga de firmas puede tardar varios minutos).

**pytest:** usa `backend/.venv`, no el `venv` de la raíz del repo:

```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'
```

---

## 7b. Perfil **waf** (ModSecurity CRS)

Requiere el override `docker-compose.waf.yml` y la imagen `WAF_IMAGE` (tag con fecha en `.env`).

```bash
docker compose -f docker-compose.yml -f docker-compose.waf.yml --profile waf up -d
./scripts/test-waf.sh
```

**502 en `/api/health` tras `docker compose up --build`:** el WAF cachea la IP de `backend` al arrancar. Si solo recreas `rag_backend`, reinicia el WAF:

```bash
bash scripts/restart-waf-after-backend.sh
# o recreación completa:
./scripts/recreate-waf.sh
```
WAF_MODE=On ./scripts/test-waf.sh
```

- `curl -fsS http://localhost/api/health` debe responder JSON del backend.
- Con `WAF_MODE=On`, un payload SQLi en query string debe devolver `403`.
- Logs de auditoría ModSecurity: `docker logs rag_waf` (o Loki con `--profile observability`; Promtail está en `docker-compose.yml`).

**pytest opcional:**

```bash
export TEST_WAF_BASE_URL=http://localhost
export WAF_MODE=On   # solo para test_sqli_query_blocked_when_waf_mode_on
cd backend && source .venv/bin/activate && pytest tests/test_waf_integration.py -v
```

O: `RUN_WAF_PYTEST=1 ./scripts/test-waf.sh` (con WAF levantado y `backend/.venv`).

**Bloqueo 403:** desde la **raíz del repo** (no desde `backend/`):

```bash
./scripts/docker-rag-clean.sh   # si hay conflictos rag_backend / rag_worker
./scripts/sync-env-security.sh  # WAF_MODE=On en .env y backend/.env
WAF_MODE=On ./scripts/recreate-waf.sh
cd backend && source .venv/bin/activate
export TEST_WAF_BASE_URL=http://localhost
pytest tests/test_waf_integration.py -v
```

## 7. Perfil **observability** (Prometheus, Grafana, Loki)

```bash
docker compose --profile observability up -d
```

- **Prometheus** (UI detrás de Traefik):

  ```bash
  curl -fsSI http://localhost/prometheus/
  ```

  Respuesta `200` o `302` a la UI.

- **Grafana** (subruta `/grafana/`):

  Abre en el navegador `http://localhost/grafana/` (usuario/contraseña por defecto del compose: `admin` / `admin_local_dev`; **cámbialos** fuera de entornos locales).

- **Loki** (solo interno en este bootstrap):

  ```bash
  docker compose exec backend wget -qO- http://loki:3100/ready
  ```

---

## 8. Rate limits (Traefik + backend)

**Importante:** los scripts viven en `scripts/` en la **raíz del repo**, no dentro de `backend/`. Desde `backend/` puedes usar los wrappers `backend/scripts/*.sh`.

Con el backend real (no placeholder) y Redis activo:

```bash
cd ~/projects/rag-local
bash scripts/sync-env-security.sh
docker compose up -d postgres redis traefik backend
bash scripts/test-rate-limits.sh
```

Pruebas automáticas (Postgres debe estar arriba **antes** de pytest):

```bash
cd ~/projects/rag-local
docker compose up -d postgres redis
source scripts/ensure-test-infra.sh   # crea rag + rag_test; exporta TEST_DATABASE_URL
cd backend && source .venv/bin/activate
pytest -q tests/test_rate_limit_unit.py tests/test_rate_limit_integration.py
```

Si ves `database "rag" does not exist`, el script actualizado crea `rag` y `rag_test` conectando a la base admin `postgres`.

O todo en uno con smoke + pytest:

```bash
RUN_RATE_LIMIT_PYTEST=1 bash scripts/test-rate-limits.sh
```

Traefik aplica `rag-ratelimit-login` (~10/min) y `rag-ratelimit-api` (~200/min) en `docker/traefik/dynamic/bootstrap.yml`.

---

## 9. Fail2ban (perfil opcional)

```bash
bash scripts/sync-env-security.sh
docker compose -f docker-compose.yml -f docker-compose.fail2ban.yml --profile fail2ban up -d
bash scripts/test-fail2ban.sh
```

En WSL2 el `banaction` es **dummy** (registra baneos sin iptables). Detalle: `docs/17-fail2ban.md`.

---

## 10. Seguridad local

- Cambia `POSTGRES_PASSWORD` y credenciales de Grafana antes de exponer la máquina a una red no confiable (p. ej. vía variables de entorno y override de Compose en una fase posterior).
- No subas `.env` al repositorio (ya ignorado en `.gitignore`).

---

## 11. Parada

```bash
docker compose down
```

Para eliminar también volúmenes nombrados (borra datos de DB/vectores/modelos):

```bash
docker compose down -v
```
