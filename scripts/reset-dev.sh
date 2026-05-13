#!/usr/bin/env bash
# Reset entorno local (destructivo). Solo usar en dev.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "[reset-dev] Raíz del repo: $ROOT"
echo "[reset-dev] TODO: docker compose down -v y recrear volúmenes cuando el flujo esté acordado."
exit 0
