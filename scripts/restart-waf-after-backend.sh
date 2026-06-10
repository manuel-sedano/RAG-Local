#!/usr/bin/env bash
# El WAF (CRS nginx) resuelve BACKEND=http://backend:80 al arrancar y guarda la IP en upstream.
# Si recreas solo rag_backend, el WAF sigue apuntando a la IP vieja → 502 en /api/*.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! docker ps --format '{{.Names}}' | grep -qx rag_waf; then
  echo "rag_waf no está en ejecución; nada que reiniciar."
  exit 0
fi

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.waf.yml --profile waf)
echo "== Reiniciando WAF para refrescar upstream backend =="
"${COMPOSE[@]}" restart waf

for _ in $(seq 1 20); do
  if docker exec rag_waf curl -sf --max-time 5 http://backend:80/api/health >/dev/null 2>&1; then
    echo "OK: WAF → backend (/api/health)"
    curl -fsS http://localhost/api/health && echo
    exit 0
  fi
  sleep 2
done

echo "ERROR: tras reiniciar WAF, sigue sin alcanzar backend. Prueba: ./scripts/recreate-waf.sh" >&2
exit 1
