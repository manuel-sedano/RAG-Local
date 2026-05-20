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

# Rate limits (Traefik + backend Redis)
upsert APP_RATE_LIMIT_ENABLED "true"
upsert APP_RATE_LIMIT_PER_MINUTE "120"
upsert INGEST_UPLOAD_MAX_PER_USER_PER_MINUTE "10"
upsert INGEST_UPLOAD_MAX_PER_KB_PER_MINUTE "20"
upsert RATE_LIMIT_AUDIT_ENABLED "true"
upsert AUTH_LOGIN_MAX_ATTEMPTS_PER_IP_PER_MINUTE "30"
upsert AUTH_LOGIN_MAX_ATTEMPTS_PER_EMAIL_PER_MINUTE "15"
# Contraseña alineada con docker-compose.yml (evita skips en pytest)
upsert POSTGRES_PASSWORD "rag_local_dev"

# backend/.env (uvicorn local): mismas vars de seguridad para tests
BACKEND_ENV="${ROOT}/backend/.env"
if [[ -f "${BACKEND_ENV}" ]]; then
  for key in WAF_MODE CLAMAV_ENABLED CLAMAV_HOST CLAMAV_PORT CLAMAV_ALLOW_EICAR_TEST \
    APP_RATE_LIMIT_ENABLED APP_RATE_LIMIT_PER_MINUTE \
    INGEST_UPLOAD_MAX_PER_USER_PER_MINUTE INGEST_UPLOAD_MAX_PER_KB_PER_MINUTE \
    RATE_LIMIT_AUDIT_ENABLED AUTH_LOGIN_MAX_ATTEMPTS_PER_IP_PER_MINUTE \
    AUTH_LOGIN_MAX_ATTEMPTS_PER_EMAIL_PER_MINUTE; do
    val="$(grep "^${key}=" "${ENV_FILE}" | cut -d= -f2- || true)"
    if [[ -n "${val}" ]]; then
      if grep -q "^${key}=" "${BACKEND_ENV}" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${val}|" "${BACKEND_ENV}"
      else
        printf '%s=%s\n' "${key}" "${val}" >> "${BACKEND_ENV}"
      fi
    fi
  done
  echo "OK: backend/.env alineado (WAF_MODE, CLAMAV_*)."
fi

echo "OK: .env actualizado (WAF, ClamAV, rate limits, COMPOSE_PROJECT_NAME=rag)."
