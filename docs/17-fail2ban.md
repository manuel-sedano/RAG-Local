# Fail2ban — estrategia y operación

**Rama:** `feat/security-fail2ban`  
**Objetivo:** bloquear IPs tras patrones de abuso (login fallido, 403/429 repetidos) leyendo logs de **Traefik**, **WAF** (opcional) y **backend**.

---

## 1) Fuentes de log

| Fuente | Ruta / canal | Patrones |
|--------|----------------|----------|
| **Traefik** | Volumen `rag_vol_traefik_logs` → `/var/log/traefik/access.log` | `POST /api/auth/login` → 401/403/429; `GET/POST /api/*` → 403 |
| **Backend FastAPI** | stdout JSON + línea `SECURITY_ACCESS …` | `client_ip`, `path=/api/auth/…`, `status=401\|403\|429` |
| **WAF ModSecurity** | stdout JSON (`MODSEC_AUDIT_LOG`) con perfil `waf` | 403 CRS (futuro: jail dedicado vía Promtail/Loki) |

El middleware `SecurityAccessLogMiddleware` emite líneas fijas para Fail2ban cuando el backend real corre con uvicorn (no el placeholder nginx).

---

## 2) Jails incluidos

| Jail | Filtro | maxretry (aprox.) | findtime | bantime |
|------|--------|---------------------|----------|---------|
| `traefik-auth` | `traefik-auth` | 5 | 10m | 1h |
| `traefik-forbidden` | `traefik-forbidden` | 20 | 10m | 30m |

Config en `docker/fail2ban/data/`.

---

## 3) Docker (perfil `fail2ban`)

```bash
docker compose -f docker-compose.yml -f docker-compose.fail2ban.yml --profile fail2ban up -d
```

- Imagen: `crazymax/fail2ban`
- **`banaction = dummy`**: registra baneos sin iptables (desarrollo en **WSL2**).
- **Linux (servidor)**: cambiar en `docker/fail2ban/data/fail2ban.local` a `iptables-multiport` y usar `network_mode: host` en `docker-compose.fail2ban.yml` (ver comentarios del archivo).

---

## 4) WSL2 vs producción

| Entorno | Comportamiento |
|---------|----------------|
| **WSL2 + Docker Desktop** | `dummy`: ver baneos en `docker logs rag_fail2ban` y `fail2ban-client status`. No corta tráfico al host Windows. |
| **Linux / VM** | `iptables-multiport` + red host para bloqueo real en firewall. |
| **Host nativo (sin contenedor F2B)** | Instalar `fail2ban` en Ubuntu y apuntar `logpath` al access.log montado en el host. |

---

## 5) Variables de entorno

| Variable | Default | Uso |
|----------|---------|-----|
| `FAIL2BAN_ENABLED` | `true` | Documentación / scripts |
| `FAIL2BAN_PROFILE` | `fail2ban` | Perfil Compose |
| `FAIL2BAN_BANACTION` | `dummy` | Referencia (config fijada en `fail2ban.local`) |
| `FAIL2BAN_SECURITY_LOG_ENABLED` | `true` | Middleware backend |
| `FAIL2BAN_SECURITY_LOG_PATH` | vacío | Archivo opcional (`/var/log/rag/security-access.log`) |

Sincronizar: `bash scripts/sync-env-security.sh`

---

## 6) Pruebas

### Automático (regex filtros)

```bash
cd backend && source .venv/bin/activate
pytest -q tests/test_fail2ban_filters.py
```

### Manual / smoke Docker

```bash
cd ~/projects/rag-local
source scripts/ensure-test-infra.sh   # si vas a probar backend real + pytest integración
bash scripts/test-fail2ban.sh
```

Tras muchos `POST /api/auth/login` fallidos o 429 (rate limit Traefik), revisar:

```bash
docker compose -f docker-compose.yml -f docker-compose.fail2ban.yml exec fail2ban fail2ban-client status traefik-auth
docker logs rag_fail2ban 2>&1 | tail -30
```

Con backend real (uvicorn), los logs también incluyen `SECURITY_ACCESS` en stdout para futuros jails Promtail.

---

## 7) Relación con otras capas

- **Rate limit** (`feat/security-rate-limits`): 429 en Traefik/backend → también cuenta para Fail2ban.
- **Auth lockout** (Redis): por usuario, no sustituye ban por IP.
- **WAF**: 403 adicionales; logs en contenedor `rag_waf` (observabilidad).
