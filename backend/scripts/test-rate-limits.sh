#!/usr/bin/env bash
# Delega al script en la raíz del repositorio (ejecutable desde backend/).
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/scripts/test-rate-limits.sh" "$@"
