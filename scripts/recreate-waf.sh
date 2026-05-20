#!/usr/bin/env bash
# Recrea Traefik + WAF con bootstrap-waf.yml y WAF_MODE del .env.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.waf.yml)

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

WAF_MODE="${WAF_MODE:-DetectionOnly}"
export WAF_MODE

echo "== Levantando traefik + backend + WAF (WAF_MODE=${WAF_MODE}) =="
"${COMPOSE[@]}" --profile waf up -d backend
"${COMPOSE[@]}" --profile waf up -d --force-recreate traefik waf

echo "== Esperando health del WAF (CRS puede tardar ~30s) =="
for _ in $(seq 1 50); do
  status="$(docker inspect -f '{{.State.Health.Status}}' rag_waf 2>/dev/null || echo starting)"
  if [[ "${status}" == "healthy" ]]; then
    echo "rag_waf healthy"
    break
  fi
  sleep 3
done

echo "== Comprobando MODSEC_RULE_ENGINE =="
docker exec rag_waf printenv MODSEC_RULE_ENGINE || true

echo "== Proxy WAF -> backend (interno) =="
if ! docker exec rag_waf curl -sf --max-time 10 http://backend:80/api/health >/dev/null; then
  echo "ERROR: el WAF no alcanza http://backend:80. Revisa red rag_net:" >&2
  docker network inspect rag_net --format '{{range .Containers}}{{.Name}} {{end}}' 2>/dev/null || true
  exit 1
fi

http_wait() {
  local url="$1"
  local want="$2"
  local label="$3"
  for _ in $(seq 1 25); do
    code="$(curl -sS -o /dev/null -w '%{http_code}' "${url}" 2>/dev/null || echo 000)"
    if [[ "${code}" == "${want}" ]]; then
      echo "${label}: HTTP ${code}"
      return 0
    fi
    sleep 2
  done
  echo "ERROR: ${label} esperaba HTTP ${want}, último=${code}" >&2
  return 1
}

echo "== Sondas vía Traefik =="
http_wait "http://localhost/api/health" "200" "GET /api/health"

if [[ "${WAF_MODE}" == "On" ]]; then
  http_wait "http://localhost/api/health?id=1%27%20OR%201%3D1--" "403" "GET SQLi"
else
  code="$(curl -sS -o /dev/null -w '%{http_code}' \
    'http://localhost/api/health?id=1%27%20OR%201%3D1--' || true)"
  echo "SQLi (DetectionOnly): HTTP ${code} (no se exige 403)"
fi

echo "OK: recreate-waf.sh"
