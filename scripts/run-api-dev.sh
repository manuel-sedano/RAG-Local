#!/usr/bin/env bash
# API FastAPI + Socket.IO para desarrollo local (WSL).
# Usar asgi_application — app.main:app NO monta /socket.io (404 → xhr poll error en el front).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
fi

export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"

echo "Arrancando API en :8000 (asgi_application con Socket.IO)…"
echo "  Swagger: http://127.0.0.1:8000/api/docs"
echo "  Socket.IO: http://127.0.0.1:8000/socket.io"
exec uvicorn app.main:asgi_application --reload --host 0.0.0.0 --port 8000
