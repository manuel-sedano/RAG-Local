#!/usr/bin/env bash
# Delega al script en la raíz (usar con: source backend/scripts/ensure-test-infra.sh)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
source "${ROOT}/scripts/ensure-test-infra.sh"
