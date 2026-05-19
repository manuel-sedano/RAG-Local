#!/usr/bin/env bash
# Pruebas de generación RAG en chat (prompting unit + integración HTTP).
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

echo "== Unitarios prompting chat =="
pytest tests/test_chat_prompting_unit.py -v --tb=short

if [[ -n "${TEST_DATABASE_URL:-}" ]]; then
  echo "== Integración POST /messages (TEST_DATABASE_URL) =="
  export QDRANT_ENABLED="${QDRANT_ENABLED:-false}"
  pytest tests/test_chat_generation_integration.py -v --tb=short
else
  echo "Omitiendo integración: export TEST_DATABASE_URL (base rag_test dedicada)."
fi
