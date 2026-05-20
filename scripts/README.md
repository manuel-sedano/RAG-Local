# Scripts operativos

Comandos pensados para **WSL / bash**. En Windows puedes ejecutarlos con `bash scripts/…`.

| Script | Propósito |
|--------|-----------|
| `run-celery-worker.sh` | **Worker de ingesta** (PDF → chunk → embed → Qdrant). Obligatorio en dev local si no usas `CELERY_TASK_ALWAYS_EAGER=true`. |
| `reset-qdrant-collection.sh` | Borra `rag_chunks_v1` tras `qdrant_dimension_mismatch`; luego reindexar documentos. |
| `backup.sh` | Stub: futuro `pg_dump` + copia de uploads. |
| `reindex.sh` | Stub: futura reindexación vía worker/API. |
| `reset-dev.sh` | Stub: futuro `docker compose down -v` documentado. |
| `sync-env-security.sh` | Alinea `.env` y `backend/.env` (WAF, ClamAV, rate limits). |
| `ensure-test-infra.sh` | Espera Postgres/Redis y crea `rag_test`; exporta `TEST_DATABASE_URL`. |
| `test-rate-limits.sh` | Smoke: Traefik + login 429; opcional `RUN_RATE_LIMIT_PYTEST=1`. |
| `test-fail2ban.sh` | Smoke Fail2ban (perfil `fail2ban`, brute-force simulado, status jail). |
| `backend/scripts/*.sh` | Wrappers para ejecutar los scripts anteriores desde `backend/`. |
| `test-waf.sh` | Smoke del WAF ModSecurity. |
| `test-clamav.sh` | Smoke de ClamAV en ingesta. |

Hazlos ejecutables en Linux/WSL:

```bash
chmod +x scripts/*.sh
```
