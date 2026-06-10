#!/usr/bin/env bash
# Smoke de observabilidad: /metrics, Prometheus scrape y Grafana.
# Uso: bash scripts/test-observability.sh
# Requiere backend en host (uvicorn :8000) o ajustar BACKEND_METRICS_URL.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source "${ROOT}/scripts/lib/load-env.sh"
load_env_file "${ROOT}/.env"

export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-rag}"

BACKEND_METRICS_URL="${BACKEND_METRICS_URL:-http://127.0.0.1:8000/metrics}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost/prometheus/-/healthy}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost/grafana/api/health}"

echo "== 1) Comprobar /metrics del backend =="
if ! curl -fsS "${BACKEND_METRICS_URL}" | head -c 400; then
  echo "AVISO: backend no expone métricas en ${BACKEND_METRICS_URL}." >&2
  echo "Arranca API: cd backend && source .venv/bin/activate && uvicorn app.main:asgi_application --host 0.0.0.0 --port 8000" >&2
  exit 1
fi
echo

echo "== 2) Levantar Traefik + perfil observability =="
docker compose up -d traefik
docker compose --profile observability up -d prometheus grafana loki promtail

echo "== 3) Esperar Prometheus =="
for i in $(seq 1 30); do
  if curl -fsS "${PROMETHEUS_URL}" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
curl -fsS "${PROMETHEUS_URL}"
echo

echo "== 4) Verificar target rag-backend UP (puede tardar 1 ciclo de scrape) =="
sleep 20
TARGETS_JSON=$(curl -fsS "http://localhost/prometheus/api/v1/targets" || echo '{}')
if echo "${TARGETS_JSON}" | grep -q '"health":"up"'; then
  echo "Al menos un target UP en Prometheus (OK)"
else
  echo "AVISO: revisa Targets en http://localhost/prometheus/targets (host.docker.internal:8000)" >&2
fi

echo "== 5) Grafana health =="
curl -fsS "${GRAFANA_URL}" | head -c 200
echo

if [ "${RUN_OBSERVABILITY_PYTEST:-0}" = "1" ]; then
  echo "== 6) pytest test_prometheus_metrics =="
  cd "${ROOT}/backend"
  # shellcheck disable=SC1091
  [ -f .venv/bin/activate ] && source .venv/bin/activate
  pytest tests/test_prometheus_metrics.py -q --tb=short
fi

echo "OK — observability smoke completado."
