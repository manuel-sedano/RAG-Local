#!/usr/bin/env bash
# Añade reglas pg_hba para conexiones desde WSL al puerto 127.0.0.1:5432 publicado.
# En Docker Desktop el servidor ve la IP del bridge (p. ej. 172.18.0.1), no 127.0.0.0.1.
apply_postgres_host_pg_hba() {
  local pg_user="${1:-rag}"
  docker compose exec -T postgres sh -eu -c "
mark='# rag-local: host access from Docker bridge/WSL'
hba=\"\${PGDATA}/pg_hba.conf\"
if ! grep -qF \"\$mark\" \"\$hba\"; then
  cat >> \"\$hba\" <<'HBAEOF'

# rag-local: host access from Docker bridge/WSL
host all all 172.16.0.0/12 scram-sha-256
host all all 10.0.0.0/8 scram-sha-256
host all all 192.168.0.0/16 scram-sha-256
HBAEOF
  psql -v ON_ERROR_STOP=1 -U \"${pg_user}\" -d postgres -c 'SELECT pg_reload_conf();' >/dev/null
  echo 'pg_hba: reglas para WSL/bridge aplicadas y recargadas.'
else
  echo 'pg_hba: reglas WSL/bridge ya presentes.'
fi
"
}
