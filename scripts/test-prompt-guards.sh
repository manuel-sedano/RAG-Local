#!/usr/bin/env bash
# Pruebas de guardrails anti prompt injection (unit + integración HTTP).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

bash "${ROOT}/scripts/sync-env-security.sh"

if [[ -d backend/.venv ]]; then
  # shellcheck disable=SC1091
  source backend/.venv/bin/activate
fi

# shellcheck disable=SC1091
source "${ROOT}/scripts/ensure-test-infra.sh"

cd "${ROOT}/backend"
pip install -q -e ".[dev]"

export ENVIRONMENT="${ENVIRONMENT:-test}"
export CHAT_LLM_BACKEND="${CHAT_LLM_BACKEND:-fake}"
export PROMPT_GUARD_ENABLED="${PROMPT_GUARD_ENABLED:-true}"
export PROMPT_GUARD_BLOCK_USER_EXFIL="${PROMPT_GUARD_BLOCK_USER_EXFIL:-true}"

echo "== Unitarios prompt guards =="
pytest tests/test_prompt_guards_unit.py -v --tb=short

if [[ -n "${TEST_DATABASE_URL:-}" ]]; then
  echo "== Integración prompt guards (TEST_DATABASE_URL) =="
  export QDRANT_ENABLED="${QDRANT_ENABLED:-false}"
  pytest tests/test_prompt_guards_integration.py -v --tb=short
else
  echo "Omitiendo integración: export TEST_DATABASE_URL (ver scripts/ensure-test-infra.sh)."
fi

echo "OK: prompt guards"
