#!/usr/bin/env bash
# Worker Celery para ingesta de documentos (antivirus → parse → chunk → embed → Qdrant).
# Sin este proceso los PDFs quedan en UPLOADED con todas las etapas PENDING.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
elif [[ -f ../.venv/bin/activate ]]; then
  # shellcheck source=/dev/null
  source ../.venv/bin/activate
fi

export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"

echo "Iniciando Celery worker (colas: ingest, ocr, embed)…"
echo "Requiere Redis en CELERY_BROKER_URL (p. ej. redis://127.0.0.1:6379/0)"
exec celery -A app.tasks.celery_app:celery_app worker \
  -Q ingest,ocr,embed \
  -l info \
  --concurrency="${CELERY_WORKER_CONCURRENCY:-2}"
