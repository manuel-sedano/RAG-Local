#!/usr/bin/env bash
# Smoke de rate limits: Traefik (perímetro) + backend Redis (login, usuario, ingesta).
# Ejecutar desde la raíz del repo: bash scripts/test-rate-limits.sh
# Desde backend/: bash scripts/test-rate-limits.sh  (wrapper en backend/scripts/)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source "${ROOT}/scripts/lib/load-env.sh"
load_env_file "${ROOT}/.env"

export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-rag}"

COMPOSE=(docker compose)
BASE="${PUBLIC_API_BASE_URL:-http://localhost/api}"
BASE="${BASE%/}"

echo "== Stack base (traefik + backend + redis + postgres) =="
"${COMPOSE[@]}" up -d traefik postgres redis backend

echo "== Esperando Postgres (host + contenedor) =="
# shellcheck disable=SC1091
source "${ROOT}/scripts/ensure-test-infra.sh"

echo "== Esperando health API =="
for i in $(seq 1 30); do
  if curl -fsS "${BASE}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
curl -fsS "${BASE}/health" | head -c 200
echo

echo "== Login rate limit (Traefik + backend; muchos POST seguidos) =="
EMAIL="${RATE_LIMIT_TEST_EMAIL:-ratelimit-smoke@example.com}"
PASS="${RATE_LIMIT_TEST_PASSWORD:-ratelimit-smoke-password-12}"
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "${BASE}/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"wrong\"}" || true

LAST=0
for n in $(seq 1 25); do
  CODE=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "${BASE}/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"${EMAIL}\",\"password\":\"wrong\"}" || echo 000)
  LAST="${CODE}"
  if [[ "${CODE}" == "429" ]]; then
    echo "429 en intento ${n} (OK)"
    break
  fi
done
if [[ "${LAST}" != "429" ]]; then
  echo "AVISO: no se obtuvo 429 en 25 intentos (revisa AUTH_* y middleware Traefik)." >&2
fi

if [ "${RUN_RATE_LIMIT_PYTEST:-0}" = "1" ]; then
  if [[ -z "${TEST_DATABASE_URL:-}" ]]; then
    echo "ERROR: TEST_DATABASE_URL vacío. Usa: source scripts/ensure-test-infra.sh" >&2
    exit 1
  fi
  export TEST_DATABASE_URL
  echo "== pytest (unit + integración; TEST_DATABASE_URL=${TEST_DATABASE_URL}) =="
  cd "${ROOT}/backend"
  if [ ! -d .venv ]; then
    echo "ERROR: crea backend/.venv antes de pytest." >&2
    exit 1
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pytest -rs tests/test_rate_limit_unit.py tests/test_rate_limit_integration.py
fi

echo "OK: test-rate-limits.sh"
