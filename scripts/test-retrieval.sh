#!/usr/bin/env bash
# Pruebas de retrieval híbrido (unit + integración opcional).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

pip install -q -e ".[dev]"

echo "== Unitarios retrieval + rerank =="
pytest tests/test_retrieval_unit.py tests/test_rerank_unit.py -v --tb=short

if [[ -n "${TEST_DATABASE_URL:-}" ]]; then
  echo "== Integración retrieval (TEST_DATABASE_URL definido) =="
  pytest tests/test_retrieval_integration.py -v --tb=short
else
  echo "Omitiendo integración: export TEST_DATABASE_URL para POST /search con Postgres."
fi
