#!/usr/bin/env bash
# Borra la colección Qdrant y la recrea en el próximo upsert.
# Usar cuando aparece ingestion_error: qdrant_dimension_mismatch
# (p. ej. cambiaste de EMBEDDING_BACKEND=fake a BAAI/bge-m3).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/load-env.sh
source "$ROOT/scripts/lib/load-env.sh"
load_env_file "$ROOT/.env"

COLLECTION="${QDRANT_COLLECTION:-rag_chunks_v1}"
HOST="${QDRANT_HOST:-127.0.0.1}"
PORT="${QDRANT_PORT:-6333}"
BASE="http://${HOST}:${PORT}"

echo "Colección: $COLLECTION"
echo "Qdrant:    $BASE"
echo ""
echo "ADVERTENCIA: se borran todos los vectores. Tras esto debes REINDEXAR cada documento (POST .../reindex)."
read -r -p "¿Continuar? [y/N] " ans
ans="${ans//$'\r'/}"
if [[ "${ans,,}" != "y" && "${ans,,}" != "yes" ]]; then
  echo "Cancelado."
  exit 0
fi

code="$(curl -s -o /tmp/qdrant-del.json -w "%{http_code}" -X DELETE "$BASE/collections/$COLLECTION")"
echo "DELETE /collections/$COLLECTION → HTTP $code"
cat /tmp/qdrant-del.json 2>/dev/null || true
echo ""

if [[ "$code" == "200" || "$code" == "404" ]]; then
  echo "Listo. Arranca el worker y reindexa los documentos FAILED/READY sin vectores:"
  echo "  bash scripts/run-celery-worker.sh"
  echo "  # luego en la UI «Reindexar» o POST /api/kbs/{kb_id}/documents/{doc_id}/reindex"
else
  echo "Error al borrar la colección. ¿Está Qdrant en marcha? curl $BASE/readyz"
  exit 1
fi
