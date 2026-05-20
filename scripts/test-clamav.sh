#!/usr/bin/env bash
# Smoke manual: ClamAV (perfil docker) + escaneo EICAR opcional.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Levantando ClamAV (puede tardar varios minutos en la primera vez)..."
docker compose --profile clamav up -d clamav

echo "==> Esperando healthcheck de clamd..."
for i in $(seq 1 60); do
  if docker compose ps clamav 2>/dev/null | grep -q "(healthy)"; then
    echo "clamd healthy"
    break
  fi
  sleep 10
  if [ "$i" -eq 60 ]; then
    echo "Timeout: revisa logs con: docker compose logs clamav"
    exit 1
  fi
done

if [ ! -f backend/app/services/antivirus/clamav.py ]; then
  echo "ERROR: falta el módulo antivirus. Haz merge de feat/security-clamav o:" >&2
  echo "  git checkout feat/security-clamav -- backend/app/services/antivirus" >&2
  exit 1
fi

echo "==> Test de integración backend (opcional EICAR real)..."
export TEST_CLAMAV=1
export CLAMAV_HOST=127.0.0.1
export CLAMAV_PORT=3310
cd backend
if [ -d .venv ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
elif [ -f ../venv/bin/activate ]; then
  echo "AVISO: usa backend/.venv (pip install -e '.[dev]'). El venv de la raíz no incluye pydantic." >&2
  exit 1
fi
pytest -q tests/test_clamav_integration.py

echo "OK: ClamAV responde y detecta EICAR."
