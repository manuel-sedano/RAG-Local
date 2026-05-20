#!/usr/bin/env bash
# Recrea el contenedor WAF aplicando WAF_MODE del .env (ej. On para bloqueo 403).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

WAF_MODE="${WAF_MODE:-DetectionOnly}"
export WAF_MODE

echo "== Recreando rag_waf con WAF_MODE=${WAF_MODE} (desde ${ROOT}) =="
docker compose -f docker-compose.yml -f docker-compose.waf.yml --profile waf up -d --force-recreate waf

echo "== Comprobando MODSEC_RULE_ENGINE en el contenedor =="
docker exec rag_waf printenv MODSEC_RULE_ENGINE || true

echo "== Sonda SQLi =="
CODE=$(curl -sS -o /dev/null -w '%{http_code}' \
  'http://localhost/api/health?id=1%27%20OR%201%3D1--' || true)
echo "HTTP ${CODE} (esperado 403 si WAF_MODE=On)"
if [[ "${WAF_MODE}" == "On" && "${CODE}" != "403" ]]; then
  echo "ERROR: WAF_MODE=On pero no hubo 403. Revisa .env y logs: docker logs rag_waf | tail -20" >&2
  exit 1
fi
