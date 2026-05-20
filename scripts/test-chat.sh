#!/usr/bin/env bash
# Pruebas de chats por KB (unit + integración con TEST_DATABASE_URL).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

pip install -q -e ".[dev]"

echo "== Unitarios chat paths =="
pytest tests/test_chat_paths.py -v --tb=short

if [[ -n "${TEST_DATABASE_URL:-}" ]]; then
  echo "== Integración chats (TEST_DATABASE_URL definido) =="
  pytest tests/test_chat_integration.py -v --tb=short
else
  echo "Omitiendo integración: export TEST_DATABASE_URL para CRUD de chats con Postgres."
fi
