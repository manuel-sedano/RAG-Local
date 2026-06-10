#!/usr/bin/env bash
# Espera Postgres/Redis y crea bases `rag` (app) y `rag_test` (pytest) si faltan.
#
# Uso recomendado (exporta TEST_DATABASE_URL en tu shell):
#   source scripts/ensure-test-infra.sh
#
# Solo comprobar (sin exportar al padre si no usas source):
#   bash scripts/ensure-test-infra.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

docker compose up -d postgres redis >/dev/null 2>&1 || true

# shellcheck disable=SC1091
source "${ROOT}/scripts/lib/load-env.sh"
load_env_file "${ROOT}/.env"

PG_HOST="${POSTGRES_HOST:-127.0.0.1}"
if [[ "${PG_HOST}" == "postgres" ]]; then
  PG_HOST="127.0.0.1"
fi
PG_PORT="${POSTGRES_PORT:-5432}"
PG_USER="${POSTGRES_USER:-rag}"
# Debe coincidir con docker-compose.yml (POSTGRES_PASSWORD); .env antiguo suele traer rag_password_local.
PG_PASS="${POSTGRES_PASSWORD:-rag_local_dev}"
if [[ "${PG_PASS}" == "rag_password_local" ]]; then
  echo "AVISO: .env usa POSTGRES_PASSWORD=rag_password_local; el contenedor usa rag_local_dev." >&2
  PG_PASS="rag_local_dev"
fi
APP_DB="${POSTGRES_DB:-rag}"
TEST_DB="${TEST_POSTGRES_DB:-rag_test}"
ADMIN_DB="postgres"

export TEST_DATABASE_URL="${TEST_DATABASE_URL:-postgresql+psycopg://${PG_USER}:${PG_PASS}@${PG_HOST}:${PG_PORT}/${TEST_DB}}"
export POSTGRES_PASSWORD="${PG_PASS}"

_psql_admin() {
  docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U "${PG_USER}" -d "${ADMIN_DB}" "$@"
}

_db_exists() {
  local name="$1"
  _psql_admin -tAc "SELECT 1 FROM pg_database WHERE datname='${name}'" 2>/dev/null | tr -d '[:space:]'
}

_ensure_database() {
  local name="$1"
  if [[ "$(_db_exists "${name}")" == "1" ]]; then
    echo "Base ${name} ya existe"
    return 0
  fi
  _psql_admin -c "CREATE DATABASE \"${name}\";"
  echo "Creada base ${name}"
}

echo "== Esperando Postgres en ${PG_HOST}:${PG_PORT} =="
for i in $(seq 1 40); do
  if docker compose exec -T postgres pg_isready -U "${PG_USER}" -d "${ADMIN_DB}" >/dev/null 2>&1; then
    echo "Postgres listo (contenedor, db=${ADMIN_DB})."
    break
  fi
  if command -v pg_isready >/dev/null 2>&1 \
    && pg_isready -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${ADMIN_DB}" >/dev/null 2>&1; then
    echo "Postgres listo (host)."
    break
  fi
  if [[ "$i" -eq 40 ]]; then
    echo "ERROR: Postgres no responde. Ejecuta: docker compose up -d postgres redis" >&2
    exit 1
  fi
  sleep 2
done

echo "== Bases de datos (admin: ${ADMIN_DB}) =="
_ensure_database "${APP_DB}"
_ensure_database "${TEST_DB}"

# shellcheck disable=SC1091
source "${ROOT}/scripts/lib/postgres-host-access.sh"
echo "== pg_hba para acceso TCP desde WSL =="
apply_postgres_host_pg_hba "${PG_USER}"

echo "== Host TCP para pytest (WSL / Docker Desktop) =="
PY="${ROOT}/backend/.venv/bin/python"
if [[ -x "${PY}" ]]; then
  RESOLVED="$(
    cd "${ROOT}/backend"
    TEST_DATABASE_URL="${TEST_DATABASE_URL}" "${PY}" -c "
from tests.postgres_url import resolve_postgres_url
import os
u = os.environ.get('TEST_DATABASE_URL', '')
r = resolve_postgres_url(u) if u else None
print(r or '', end='')
"
  )"
  if [[ -n "${RESOLVED}" ]]; then
    export TEST_DATABASE_URL="${RESOLVED}"
    echo "Conexión OK desde el host → ${TEST_DATABASE_URL}"
  else
    echo "ERROR: Postgres no responde por TCP desde WSL (pytest)." >&2
    echo "  1) source scripts/ensure-test-infra.sh  (aplica pg_hba para bridge Docker)" >&2
    echo "  2) nc -zv 127.0.0.1 ${PG_PORT}  y POSTGRES_PASSWORD=rag_local_dev en .env" >&2
    echo "  3) docker compose restart postgres" >&2
    exit 1
  fi
else
  echo "AVISO: sin backend/.venv; no se validó TCP al host." >&2
fi

echo "TEST_DATABASE_URL=${TEST_DATABASE_URL}"
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  echo "OK: variables exportadas en el shell actual (source)."
else
  echo ""
  echo "Para pytest en este terminal, ejecuta:"
  echo "  export TEST_DATABASE_URL='${TEST_DATABASE_URL}'"
  echo "O vuelve a cargar con: source scripts/ensure-test-infra.sh"
fi
echo "OK: ensure-test-infra.sh"
