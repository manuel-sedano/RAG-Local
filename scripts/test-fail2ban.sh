#!/usr/bin/env bash
# Smoke Fail2ban: Traefik access.log + jail traefik-auth (modo dummy en WSL).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source "${ROOT}/scripts/lib/load-env.sh"
load_env_file "${ROOT}/.env"

export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-rag}"
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.fail2ban.yml)
BASE="${PUBLIC_API_BASE_URL:-http://localhost/api}"
BASE="${BASE%/}"

echo "== Filtros Fail2ban (pytest unitario) =="
PYTEST_OK=1
if [[ -x "${ROOT}/backend/.venv/bin/python" ]]; then
  cd "${ROOT}/backend"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  if ! pytest -q tests/test_fail2ban_filters.py; then
    PYTEST_OK=0
    echo "AVISO: pytest de filtros falló (se continúa con smoke Docker)." >&2
  fi
  cd "${ROOT}"
else
  echo "AVISO: omite pytest (crea backend/.venv)" >&2
fi

echo "== Recrear traefik (access.log) + fail2ban =="
"${COMPOSE[@]}" --profile fail2ban up -d --force-recreate traefik fail2ban

echo "== Esperando contenedor fail2ban =="
F2B_OK=0
for i in $(seq 1 40); do
  if docker inspect -f '{{.State.Health.Status}}' rag_fail2ban 2>/dev/null | grep -q healthy; then
    F2B_OK=1
    echo "rag_fail2ban healthy"
    break
  fi
  if docker inspect -f '{{.State.Running}}' rag_fail2ban 2>/dev/null | grep -q false; then
    echo "ERROR: rag_fail2ban no está en ejecución. Logs:" >&2
    docker logs rag_fail2ban 2>&1 | tail -n 40 >&2 || true
    break
  fi
  sleep 3
done
if [[ "${F2B_OK}" -ne 1 ]]; then
  echo "ERROR: fail2ban no pasó healthcheck. Revisa: docker logs rag_fail2ban" >&2
  exit 1
fi

echo "== Simulación brute-force en login (401/429 en access.log) =="
EMAIL="${FAIL2BAN_TEST_EMAIL:-fail2ban-test@example.com}"
for n in $(seq 1 30); do
  curl -sS -o /dev/null -w '%{http_code}\n' -X POST "${BASE}/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"${EMAIL}\",\"password\":\"wrong-password-${n}\"}" || true
done

echo "== Últimas líneas access.log Traefik =="
docker compose exec -T traefik tail -n 8 /var/log/traefik/access.log 2>/dev/null || true

echo "== Estado jail traefik-auth =="
sleep 8
"${COMPOSE[@]}" exec -T fail2ban fail2ban-client status traefik-auth || true

echo "== Banned IPs (dummy banaction) =="
docker logs rag_fail2ban 2>&1 | tail -n 25 | grep -iE 'ban|Ban' || echo "(sin 'ban' aún; baja maxretry o repite curls)"

if [[ "${PYTEST_OK}" -ne 1 ]]; then
  exit 1
fi
echo "OK: test-fail2ban.sh"
