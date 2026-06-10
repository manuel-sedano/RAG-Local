#!/usr/bin/env bash
# Smoke de logs estructurados + Loki/Promtail.
# Uso: bash scripts/test-observability-logs.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source "${ROOT}/scripts/lib/load-env.sh"
load_env_file "${ROOT}/.env"

export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-rag}"
mkdir -p "${ROOT}/uploads/logs"

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
LOKI_URL="${LOKI_URL:-http://localhost:3100/ready}"

echo "== 1) Generar tráfico API (access log JSON) =="
if curl -fsS "${BACKEND_URL}/api/health" >/dev/null 2>&1; then
  curl -fsS "${BACKEND_URL}/api/health" | head -c 120
  echo
else
  echo "AVISO: API no en ${BACKEND_URL}. Arranca uvicorn en :8000." >&2
fi

echo "== 2) Comprobar archivo JSONL local =="
sleep 1
if ls "${ROOT}/uploads/logs/"*.jsonl >/dev/null 2>&1; then
  tail -n 2 "${ROOT}/uploads/logs/"*.jsonl | head -c 500
  echo
else
  echo "AVISO: aún no hay uploads/logs/*.jsonl (LOG_FILE_ENABLED=true y API activa)." >&2
fi

echo "== 3) Levantar Loki + Promtail =="
docker compose up -d traefik
docker compose --profile observability up -d loki promtail grafana

echo "== 4) Esperar Loki =="
for i in $(seq 1 20); do
  if docker compose exec -T loki wget -qO- http://127.0.0.1:3100/ready 2>/dev/null | grep -q ready; then
    break
  fi
  sleep 2
done
docker compose exec -T loki wget -qO- http://127.0.0.1:3100/ready || true
echo

echo "== 5) Query Loki (últimos logs JSON) =="
sleep 5
QUERY='{job="rag-app-files"}'
ENCODED=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "${QUERY}")
NOW=$(date +%s)
START=$((NOW - 3600))
RESULT=$(curl -fsS "http://localhost:3100/loki/api/v1/query_range?query=${ENCODED}&limit=5&start=${START}000000000&end=${NOW}000000000" 2>/dev/null || echo '{}')
if echo "${RESULT}" | grep -q '"status":"success"'; then
  echo "Loki respondió OK (revisa Grafana → RAG Local — Logs)"
else
  echo "AVISO: sin resultados aún; espera scrape Promtail o genera más tráfico." >&2
fi

if [ "${RUN_LOGGING_PYTEST:-0}" = "1" ]; then
  echo "== 6) pytest logging =="
  cd "${ROOT}/backend"
  # shellcheck disable=SC1091
  [ -f .venv/bin/activate ] && source .venv/bin/activate
  pytest tests/test_logging_correlation.py -q --tb=short
fi

echo "OK — observability logs smoke completado."
