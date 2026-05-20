#!/usr/bin/env bash
# Alinea variables de seguridad en .env (desde .env.example si faltan).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ROOT}/.env"
EXAMPLE="${ROOT}/.env.example"

if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${EXAMPLE}" "${ENV_FILE}"
  echo "Creado .env desde .env.example"
fi

upsert() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" "${ENV_FILE}" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "${ENV_FILE}"
  else
    printf '%s=%s\n' "${key}" "${value}" >> "${ENV_FILE}"
  fi
}

# Imagen WAF válida
upsert COMPOSE_PROJECT_NAME "rag"
upsert WAF_IMAGE "owasp/modsecurity-crs:4-nginx-alpine-202509220609"
# Bloqueo CRS (cambiar a DetectionOnly en prod observación)
upsert WAF_MODE "On"
upsert WAF_ENABLED "true"
upsert WAF_MAX_BODY_BYTES "52428800"

# ClamAV local + tests EICAR en dev
upsert CLAMAV_ENABLED "true"
upsert CLAMAV_HOST "clamav"
upsert CLAMAV_PORT "3310"
upsert CLAMAV_TIMEOUT_SECONDS "120"
upsert CLAMAV_FAIL_OPEN "false"
upsert CLAMAV_ALLOW_EICAR_TEST "true"

echo "OK: .env actualizado (WAF_MODE=On, CLAMAV_*, WAF_IMAGE)."
