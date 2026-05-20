#!/usr/bin/env bash
# Smoke del WAF ModSecurity (Traefik -> WAF -> backend).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.waf.yml)
WAF_MODE="${WAF_MODE:-DetectionOnly}"
export WAF_MODE

echo "== Levantando stack con perfil waf (WAF_MODE=${WAF_MODE}) =="
"${COMPOSE[@]}" --profile waf up -d traefik backend waf

echo "== Esperando health del WAF =="
for i in $(seq 1 40); do
  if docker inspect -f '{{.State.Health.Status}}' rag_waf 2>/dev/null | grep -q healthy; then
    break
  fi
  sleep 3
done

echo "== API health via Traefik/WAF =="
curl -fsS http://localhost/api/health | head -c 200
echo

echo "== Payload sospechoso (SQLi en query) =="
CODE=$(curl -sS -o /tmp/waf-test-body.txt -w '%{http_code}' \
  'http://localhost/api/health?id=1%27%20OR%201%3D1--' || true)
echo "HTTP ${CODE}"
if [[ "${WAF_MODE}" == "On" && "${CODE}" != "403" ]]; then
  echo "ERROR: con WAF_MODE=On se esperaba 403" >&2
  exit 1
fi
if [[ "${WAF_MODE}" == "DetectionOnly" ]]; then
  echo "Modo DetectionOnly: no se exige 403 (revisar audit en logs del contenedor rag_waf)."
fi

echo "== Ultimas lineas de audit ModSecurity =="
docker logs rag_waf 2>&1 | tail -n 15 || true

echo "OK: test-waf.sh"