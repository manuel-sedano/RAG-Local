#!/usr/bin/env bash
set +e
cd /home/manuel-sedano/projects/rag-local
exec > _agent_run.log 2>&1
git checkout feat/doc-parsers 2>/dev/null || git checkout -b feat/doc-parsers
echo "EXIT_git_checkout=$?"
echo "BRANCH=$(git branch --show-current)"
cd backend
source .venv/bin/activate 2>/dev/null || { python3 -m venv .venv && source .venv/bin/activate; }
pip install -e ".[dev]" -q
echo "EXIT_pip=$?"
echo "=== pytest doc_parsers + settings ==="
pytest tests/test_doc_parsers.py tests/test_settings.py -v --tb=short
echo "EXIT_pytest1=$?"
export TEST_DATABASE_URL="${TEST_DATABASE_URL:-postgresql+psycopg://rag:rag_local_dev@127.0.0.1:5432/rag_test}"
echo "TEST_DATABASE_URL=$TEST_DATABASE_URL"
echo "=== pytest ingestion ==="
pytest tests/test_ingestion_worker.py::test_ingest_success_state_transition -v --tb=short
echo "EXIT_pytest2=$?"
echo "=== ruff ==="
ruff check app tests
echo "EXIT_ruff=$?"
echo "=== black ==="
python -m black --check app tests
echo "EXIT_black=$?"
