#!/usr/bin/env bash
# Pruebas Socket.IO (auth unit + streaming mock con TEST_DATABASE_URL).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

pip install -q -e ".[dev]"

export ENVIRONMENT="${ENVIRONMENT:-test}"
export CHAT_LLM_BACKEND="${CHAT_LLM_BACKEND:-fake}"
export SOCKETIO_ENABLED="${SOCKETIO_ENABLED:-true}"

echo "== Unitarios auth Socket.IO =="
pytest tests/test_socketio_auth.py -v --tb=short

if [[ -n "${TEST_DATABASE_URL:-}" ]]; then
  echo "== Streaming mock (TEST_DATABASE_URL) =="
  export QDRANT_ENABLED="${QDRANT_ENABLED:-false}"
  pytest tests/test_socketio_streaming.py -v --tb=short
else
  echo "Omitiendo streaming: export TEST_DATABASE_URL"
fi
